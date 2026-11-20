import os

from app.publisher import MockLinkedInPublisher, MockXPublisher, SocialPublisher

_REGISTRY: dict[str, SocialPublisher] = {
    "mock_x": MockXPublisher(),
    "mock_linkedin": MockLinkedInPublisher(),
}

# Default adapter per platform. Telegram points at a mock until Phase 4b.
_DEFAULTS = {"x": "mock_x", "linkedin": "mock_linkedin", "telegram": "mock_x"}


def get_publisher(platform: str) -> SocialPublisher:
    name = os.environ.get(f"ADAPTER_{platform.upper()}", _DEFAULTS[platform])
    if name not in _REGISTRY:
        raise ValueError(f"Unknown adapter '{name}' for platform '{platform}'")
    return _REGISTRY[name]