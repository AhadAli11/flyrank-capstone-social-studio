from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.db import get_conn


@dataclass
class PublishResult:
    ok: bool
    external_id: str | None = None
    detail: str = ""


class SocialPublisher(ABC):
    name: str

    @abstractmethod
    def publish(self, text: str, idempotency_key: str) -> PublishResult:
        """Publish text. Calling twice with the same key must create only one post."""


class MockPublisher(SocialPublisher):
    """Records what it WOULD post in the database. No network."""

    def publish(self, text: str, idempotency_key: str) -> PublishResult:
        with get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO mock_posts (adapter, idempotency_key, text) VALUES (?, ?, ?)",
                (self.name, idempotency_key, text),
            )
            row = conn.execute(
                "SELECT id FROM mock_posts WHERE adapter = ? AND idempotency_key = ?",
                (self.name, idempotency_key),
            ).fetchone()
        return PublishResult(
            ok=True,
            external_id=f"{self.name}-{row['id']}",
            detail=f"Recorded by mock adapter. Preview: {text[:80]}",
        )


class MockXPublisher(MockPublisher):
    name = "mock_x"


class MockLinkedInPublisher(MockPublisher):
    name = "mock_linkedin"