# Design: Social Media Studio

## Problem
Marketing teams turn one blog post into several platform posts by hand.
This service ingests a post, generates one variant per platform, enforces each
platform's rules, requires human approval, and publishes approved variants on
schedule exactly once, even under retries and crashes.

## Platforms and constraint profiles
| Platform | Max length | Tone | Max hashtags |
|---|---|---|---|
| x | 280 | short, punchy | 2 |
| linkedin | 3000 | professional | 5 |
| telegram | 4096 | friendly, plain | 3 |

Targets: telegram (real, my own channel), mock_x and mock_linkedin (mock adapters).

## Data model (SQLite)
- posts: id, source_type (url|markdown), source_url, title, body, created_at
- variants: id, post_id, platform, text, status
  (draft|approved|rejected|published), created_at
- slots: id, variant_id, publish_at, status (pending|done|failed), idempotency_key (unique)
- publish_attempts: id, slot_id, adapter, result (success|failure), detail,
  external_id, created_at

## SocialPublisher interface
publish(text: str, idempotency_key: str) -> PublishResult
- PublishResult: ok, external_id, detail
- Same idempotency_key twice returns the first result and creates no second post.

Implementations: TelegramPublisher, MockXPublisher, MockLinkedInPublisher.
The active adapter per platform is chosen from config, not in business logic.

## API surface
- POST /posts - ingest (URL or markdown), returns post id
- POST /posts/{id}/variants - generate variants for configured platforms
- GET /posts/{id}/variants - list variants
- POST /variants/{id}/approve | /reject
- PUT /variants/{id} - edit text (revalidated, returns to draft)
- POST /variants/{id}/schedule - body {publish_at}; 4xx if not approved
- GET /history - publish attempts

## Idempotency key
"<variant_id>:<slot_id>" - one variant in one slot can post only once.

## Non-goal
No image generation, analytics, or real Instagram/X/LinkedIn accounts.