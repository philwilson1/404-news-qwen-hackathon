"""Central configuration. Everything is read from environment variables so the
same code runs locally, on Render, and in GitHub Actions."""
import os
from dataclasses import dataclass, field
from typing import List, Mapping


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    try:
        return int(env.get(name, default))
    except (TypeError, ValueError):
        return default


def _list(env: Mapping[str, str], name: str, default: str) -> List[str]:
    return [x.strip() for x in env.get(name, default).split(",") if x.strip()]


@dataclass
class Settings:
    # --- Groq (free tier) ---
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    # Groq retires models regularly (llama-3.3-70b-versatile and llama-3.1-8b-instant
    # were shut down on 2026-08-16). Override these in the environment, no code change needed.
    model: str = "openai/gpt-oss-120b"          # chat + tool calling
    fast_model: str = "openai/gpt-oss-20b"      # digests / cheap calls
    fallback_models: List[str] = field(default_factory=lambda: ["openai/gpt-oss-20b"])
    reasoning_effort: str = "low"               # "" disables the parameter
    rpm: int = 25                               # stay under the free-tier 30 requests/minute
    max_wait_s: int = 20                        # longest 429 retry-after we will sleep through
    request_timeout_s: int = 60

    # --- News sources ---
    news_lang: str = "en"
    news_region: str = "NG"
    topic_max_age_days: int = 7
    articles_per_topic: int = 8

    # --- Limits ---
    max_topics_per_user: int = 10               # keep in sync with supabase/001_topics.sql
    digest_pause_s: float = 3.0                 # pause between topics in a batch refresh

    # --- Supabase ---
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    pipeline_secret: str = ""

    # --- Web ---
    allowed_origins: List[str] = field(default_factory=list)


DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "https://404-news-qwen-hackathon.vercel.app",
]


def load_settings(env: Mapping[str, str] = os.environ) -> Settings:
    return Settings(
        groq_api_key=env.get("GROQ_API_KEY", ""),
        groq_base_url=env.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/"),
        model=env.get("GROQ_MODEL", "openai/gpt-oss-120b"),
        fast_model=env.get("GROQ_FAST_MODEL", "openai/gpt-oss-20b"),
        fallback_models=_list(env, "GROQ_FALLBACK_MODELS", "openai/gpt-oss-20b"),
        reasoning_effort=env.get("GROQ_REASONING_EFFORT", "low"),
        rpm=max(1, _int(env, "GROQ_RPM", 25)),
        max_wait_s=_int(env, "GROQ_MAX_WAIT_S", 20),
        news_lang=env.get("NEWS_LANG", "en"),
        news_region=env.get("NEWS_REGION", "NG"),
        topic_max_age_days=_int(env, "TOPIC_MAX_AGE_DAYS", 7),
        articles_per_topic=_int(env, "ARTICLES_PER_TOPIC", 8),
        max_topics_per_user=_int(env, "MAX_TOPICS_PER_USER", 10),
        digest_pause_s=float(env.get("DIGEST_PAUSE_S", 3)),
        supabase_url=env.get("SUPABASE_URL", ""),
        supabase_anon_key=env.get("SUPABASE_ANON_KEY", ""),
        supabase_service_key=env.get("SUPABASE_SERVICE_KEY", ""),
        pipeline_secret=env.get("PIPELINE_SECRET", ""),
        allowed_origins=DEFAULT_ORIGINS + _list(env, "ALLOWED_ORIGINS", ""),
    )
