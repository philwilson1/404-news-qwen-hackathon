"""Minimal Groq client (OpenAI-compatible REST API) built on `requests`.

Why not an SDK: fewer dependencies on a free host, and full control over the things
the free tier needs: request pacing, 429 handling, and falling back to another model
when one is rate limited or retired.
"""
import json
import threading
import time
from typing import Any, Dict, Iterator, List, Optional

import requests

from config import Settings


class LLMError(Exception):
    def __init__(self, message: str, status: Optional[int] = None, code: str = ""):
        super().__init__(message)
        self.status = status
        self.code = code

    @property
    def public_message(self) -> str:
        if self.status == 401:
            return "The AI service rejected our API key. The server needs a valid GROQ_API_KEY."
        if self.status == 429:
            return "The AI service is at its free-tier limit right now. Please try again in a minute."
        return "The AI service had a problem. Please try again shortly."


def _error_info(resp) -> Dict[str, str]:
    try:
        err = resp.json().get("error", {})
        return {"message": str(err.get("message", "")), "code": str(err.get("code", "") or err.get("type", ""))}
    except Exception:
        return {"message": getattr(resp, "text", "") or "", "code": ""}


def _retry_after(resp) -> float:
    try:
        return float(resp.headers.get("retry-after", "0") or 0)
    except (TypeError, ValueError):
        return 0.0


class GroqClient:
    def __init__(self, settings: Settings, session=None, sleep=time.sleep, clock=time.monotonic):
        self.s = settings
        self.session = session or requests.Session()
        self._sleep = sleep
        self._clock = clock
        self._lock = threading.Lock()
        self._last = -1e9

    # ---- pacing -------------------------------------------------------
    def _throttle(self) -> None:
        interval = 60.0 / self.s.rpm
        with self._lock:
            wait = self._last + interval - self._clock()
            if wait > 0:
                self._sleep(wait)
            self._last = self._clock()

    # ---- models -------------------------------------------------------
    def _models(self, primary: str) -> List[str]:
        out: List[str] = []
        for m in [primary, *self.s.fallback_models, self.s.model]:
            if m and m not in out:
                out.append(m)
        return out

    # ---- HTTP ---------------------------------------------------------
    def _request(self, payload: Dict[str, Any], primary: str, stream: bool):
        if not self.s.groq_api_key:
            raise LLMError("GROQ_API_KEY is not set on the server.", status=401)
        url = f"{self.s.groq_base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.s.groq_api_key}", "Content-Type": "application/json"}
        last_err: Optional[LLMError] = None

        for model in self._models(primary):
            body = dict(payload, model=model, stream=stream)
            if self.s.reasoning_effort and model.startswith("openai/gpt-oss"):
                body["reasoning_effort"] = self.s.reasoning_effort
            attempts = 0
            while attempts < 3:
                attempts += 1
                self._throttle()
                try:
                    resp = self.session.post(url, json=body, headers=headers,
                                             timeout=self.s.request_timeout_s, stream=stream)
                except requests.RequestException as e:
                    last_err = LLMError(f"Network error talking to Groq: {e}")
                    if attempts < 2:
                        self._sleep(1.5)
                        continue
                    break
                status = resp.status_code
                if status == 200:
                    resp.groq_model = model  # type: ignore[attr-defined]
                    return resp
                info = _error_info(resp)
                msg, code = info["message"], info["code"]
                resp.close()
                last_err = LLMError(msg or f"Groq returned HTTP {status}", status=status, code=code)

                if status == 401:
                    raise last_err
                if status == 429:
                    wait = _retry_after(resp)
                    daily = "per day" in msg.lower() or "(tpd)" in msg.lower() or "(rpd)" in msg.lower()
                    if not daily and wait <= self.s.max_wait_s and attempts < 2:
                        self._sleep(max(wait, 1.0))
                        continue
                    break  # try the next model: limits are tracked per model
                if status in (404, 410) or code in ("model_not_found", "model_decommissioned") \
                        or "decommissioned" in msg.lower():
                    break  # retired or unknown model, try the next one
                if status == 400 and "reasoning_effort" in msg and "reasoning_effort" in body:
                    body.pop("reasoning_effort")
                    continue
                if status == 400 and (code == "tool_use_failed" or "tool_use_failed" in msg):
                    raise LLMError(msg, status=400, code="tool_use_failed")
                if status >= 500 and attempts < 2:
                    self._sleep(1.5)
                    continue
                if status >= 500:
                    break
                raise last_err  # other 4xx: our request is wrong, a new model will not help
        raise last_err or LLMError("No model available")

    # ---- public API ---------------------------------------------------
    def complete(self, messages: List[dict], *, model: Optional[str] = None, max_tokens: int = 600,
                 temperature: float = 0.3, tools: Optional[list] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        if tools:
            payload["tools"] = tools
        resp = self._request(payload, model or self.s.fast_model, stream=False)
        try:
            msg = resp.json()["choices"][0]["message"]
        except (KeyError, IndexError, ValueError) as e:
            raise LLMError(f"Unexpected response from Groq: {e}")
        return {"content": msg.get("content") or "", "tool_calls": msg.get("tool_calls") or [],
                "model": resp.groq_model}

    def stream_chat(self, messages: List[dict], *, tools: Optional[list] = None, model: Optional[str] = None,
                    max_tokens: int = 2500, temperature: float = 0.4) -> Iterator[Dict[str, Any]]:
        """Yields {"type": "text", "text": str} as tokens arrive, then one
        {"type": "done", "content": str, "tool_calls": [...], "model": str}."""
        payload: Dict[str, Any] = {"messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        resp = self._request(payload, model or self.s.model, stream=True)
        content_parts: List[str] = []
        calls: Dict[int, Dict[str, Any]] = {}
        try:
            for raw in resp.iter_lines():  # bytes: the stream has no charset, so requests would guess Latin-1
                if not raw:
                    continue
                line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except ValueError:
                    continue
                if chunk.get("error"):
                    raise LLMError(str(chunk["error"].get("message", "stream error")))
                for choice in chunk.get("choices", []):
                    delta = choice.get("delta") or {}
                    text = delta.get("content")
                    if text:
                        content_parts.append(text)
                        yield {"type": "text", "text": text}
                    for tc in delta.get("tool_calls") or []:
                        slot = calls.setdefault(tc.get("index", 0), {"id": "", "name": "", "arguments": ""})
                        if tc.get("id"):
                            slot["id"] = tc["id"]
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            slot["name"] = fn["name"]
                        if fn.get("arguments"):
                            slot["arguments"] += fn["arguments"]
        finally:
            resp.close()
        tool_calls = [
            {"id": c["id"] or f"call_{i}", "type": "function",
             "function": {"name": c["name"], "arguments": c["arguments"] or "{}"}}
            for i, c in sorted(calls.items()) if c["name"]
        ]
        yield {"type": "done", "content": "".join(content_parts), "tool_calls": tool_calls, "model": resp.groq_model}
