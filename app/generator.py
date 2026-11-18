import re

from app.profiles import PROFILES


def _clean(body: str) -> str:
    lines = [line for line in body.splitlines() if not line.startswith("#")]
    text = " ".join(line.strip() for line in lines if line.strip())
    return re.sub(r"[*_`>]", "", text)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p for p in parts if p] or [text]


def _hashtags(title: str, limit: int) -> str:
    seen = []
    for word in re.findall(r"[A-Za-z]{5,}", title):
        tag = "#" + word.lower()
        if tag not in seen:
            seen.append(tag)
    return " ".join(seen[:limit])


def _shorten(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def generate_variant(platform: str, title: str, body: str) -> str:
    profile = PROFILES[platform]
    sentences = _sentences(_clean(body))
    tags = _hashtags(title, profile["max_hashtags"])

    if platform == "x":
        room = profile["max_length"] - len(tags) - 1
        text = _shorten(f"{title}. {sentences[0]}", room)
        return f"{text} {tags}".strip()

    if platform == "linkedin":
        points = "\n\n".join(sentences[:4])
        return f"{title}\n\n{points}\n\nWhat is your experience with this?\n\n{tags}".strip()

    if platform == "telegram":
        text = f"New post: {title}\n\n{sentences[0]}\n\n{tags}".strip()
        return _shorten(text, profile["max_length"])

    raise ValueError(f"No generator for platform '{platform}'")
        