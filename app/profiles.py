PROFILES = {
    "x": {
        "max_length": 280,
        "max_hashtags": 2,
        "tone": "short, punchy",
        "banned_phrases": [],
    },
    "linkedin": {
        "max_length": 3000,
        "max_hashtags": 5,
        "tone": "professional",
        "banned_phrases": ["lol", "omg", "!!!"],
    },
    "telegram": {
        "max_length": 4096,
        "max_hashtags": 3,
        "tone": "friendly, plain",
        "banned_phrases": [],
    },
}

PLATFORMS = list(PROFILES)
