"""Fetch a news article and pull out its readable text (standard library + requests only).

Used by the chat agent's read_article tool so it can give real detail on one story instead of
guessing from a headline. Safe by design: http(s) only, private/internal addresses are blocked,
redirects are re-checked, and downloads are size-capped.
"""
import ipaddress
import socket
from html.parser import HTMLParser
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse

import requests

USER_AGENT = "Mozilla/5.0 (compatible; 404NewsBot/2.0; +https://404-news-qwen-hackathon.vercel.app)"
TIMEOUT_S = 10
MAX_BYTES = 1_500_000
MAX_REDIRECTS = 4
DEFAULT_MAX_CHARS = 3500

_SKIP = {"script", "style", "noscript", "svg", "nav", "header", "footer", "aside", "form", "iframe", "figure"}


class ReaderError(Exception):
    """Message is safe to show to the model."""


def _is_public_host(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved \
                or ip.is_unspecified:
            return False
    return bool(infos)


def _check_url(url: str) -> str:
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ReaderError("That is not a valid web link.")
    if not _is_public_host(p.hostname):
        raise ReaderError("That link cannot be opened.")
    return p.hostname


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta_desc = ""
        self._in_title = False
        self._skip = 0
        self._article = 0
        self._p = 0
        self._buf = []
        self.article_paras = []   # paragraphs found inside <article>
        self.all_paras = []       # every paragraph on the page

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            if key in ("og:description", "description", "twitter:description") and not self.meta_desc:
                self.meta_desc = (a.get("content") or "").strip()
            if key == "og:title" and not self.title:
                self.title = (a.get("content") or "").strip()
        elif tag in _SKIP:
            self._skip += 1
        elif tag == "article":
            self._article += 1
        elif tag in ("p", "h2", "h3", "li") and not self._skip:
            self._p += 1
            self._buf = []

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in _SKIP:
            self._skip = max(0, self._skip - 1)
        elif tag == "article":
            self._article = max(0, self._article - 1)
        elif tag in ("p", "h2", "h3", "li") and self._p:
            self._p -= 1
            text = " ".join("".join(self._buf).split())
            self._buf = []
            if len(text) >= 40:
                self.all_paras.append(text)
                if self._article:
                    self.article_paras.append(text)

    def handle_data(self, data):
        if self._in_title and not self.title:
            self.title = data.strip()
        if self._p and not self._skip:
            self._buf.append(data)


def extract_text(html: str, max_chars: int = DEFAULT_MAX_CHARS) -> Dict[str, str]:
    """Return {"title", "text"} from raw HTML. Prefers <article> paragraphs over the whole page."""
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        pass
    paras = parser.article_paras if len(" ".join(parser.article_paras)) > 400 else parser.all_paras
    seen, kept = set(), []
    for para in paras:
        if para not in seen:
            seen.add(para)
            kept.append(para)
    text = "\n\n".join(kept) or parser.meta_desc
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + " ..."
    return {"title": parser.title[:200], "text": text}


def fetch_article_text(url: str, max_chars: int = DEFAULT_MAX_CHARS, session: Optional[requests.Session] = None) -> Dict[str, str]:
    """Download the page and return {"title", "text", "host"}. Raises ReaderError with a model-safe message."""
    sess = session or requests.Session()
    current = url
    resp = None
    for _ in range(MAX_REDIRECTS + 1):
        host = _check_url(current)
        try:
            resp = sess.get(current, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.5"},
                            timeout=TIMEOUT_S, stream=True, allow_redirects=False)
        except requests.RequestException:
            raise ReaderError("The article site did not respond.")
        if resp.status_code in (301, 302, 303, 307, 308) and resp.headers.get("location"):
            current = urljoin(current, resp.headers["location"])
            resp.close()
            continue
        break
    else:
        raise ReaderError("The link redirected too many times.")

    try:
        if resp.status_code != 200:
            raise ReaderError(f"The article site returned an error (HTTP {resp.status_code}); it may block bots "
                              "or sit behind a paywall.")
        ctype = resp.headers.get("content-type", "").lower()
        if "html" not in ctype and "text" not in ctype:
            raise ReaderError("That link is not a readable web page.")
        chunks, size = [], 0
        for chunk in resp.iter_content(65536):
            size += len(chunk)
            if size > MAX_BYTES:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        enc = resp.encoding if resp.encoding and "charset" in ctype else "utf-8"
    finally:
        resp.close()

    final_host = urlparse(current).hostname or host
    if final_host.endswith("news.google.com"):
        raise ReaderError("This link is a Google News redirect that cannot be opened from the server. "
                          "Use the headline only and point the user to the linked article.")
    out = extract_text(raw.decode(enc or "utf-8", errors="replace"), max_chars)
    if len(out["text"]) < 200:
        raise ReaderError("Could not extract readable text from that page (it may be paywalled or load its content "
                          "with JavaScript).")
    out["host"] = final_host.removeprefix("www.")
    return out
