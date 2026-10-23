"""Topic name normalisation. The frontend uses the same algorithm
(slugifyTopic in src/lib/supabase.ts) so both sides agree on slugs."""
import re
import unicodedata
from typing import Tuple

MIN_LEN = 2
MAX_LEN = 60


def slugify(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")
    return slug[:MAX_LEN].strip("-")


def normalize_topic(raw: str) -> Tuple[str, str]:
    """Returns (display_topic, slug) or raises ValueError with a user-facing message."""
    topic = " ".join((raw or "").split())
    if len(topic) < MIN_LEN:
        raise ValueError("Give me a topic to follow, for example 'quantum computing'.")
    if len(topic) > MAX_LEN:
        raise ValueError(f"That topic is too long. Keep it under {MAX_LEN} characters.")
    slug = slugify(topic)
    if not slug:
        raise ValueError("The topic needs some letters or numbers.")
    return topic, slug


def topic_category(slug: str) -> str:
    """Value stored in articles.category for a followed topic."""
    return f"topic-{slug}"
