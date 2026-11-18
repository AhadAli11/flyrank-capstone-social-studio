import re

from app.profiles import PROFILES


def validate(platform: str, text: str) -> list[str]:
    profile = PROFILES[platform]
    errors = []

    if not text.strip():
        errors.append("Text is empty.")

    if len(text) > profile["max_length"]:
        errors.append(
            f"Length rule broken: {len(text)} characters, "
            f"{platform} allows at most {profile['max_length']}."
        )

    hashtag_count = len(re.findall(r"#\w+", text))
    if hashtag_count > profile["max_hashtags"]:
        errors.append(
            f"Hashtag rule broken: {hashtag_count} hashtags, "
            f"{platform} allows at most {profile['max_hashtags']}."
        )

    lowered = text.lower()
    for phrase in profile["banned_phrases"]:
        if phrase in lowered:
            errors.append(
                f"Tone rule broken: '{phrase}' is not allowed on {platform} "
                f"(tone: {profile['tone']})."
            )

    return errors