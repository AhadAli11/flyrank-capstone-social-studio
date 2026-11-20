from app.adapters import get_publisher
from app.db import get_conn


class PublishError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message


def publish_slot(slot_id: int) -> dict:
    with get_conn() as conn:
        slot = conn.execute("SELECT * FROM slots WHERE id = ?", (slot_id,)).fetchone()
        if slot is None:
            raise PublishError(404, "Slot not found.")

        # Layer 1: already published, so return the earlier result.
        if slot["status"] == "done":
            previous = conn.execute(
                "SELECT * FROM publish_attempts WHERE slot_id = ? AND result = 'success' ORDER BY id LIMIT 1",
                (slot_id,),
            ).fetchone()
            return {
                "slot_id": slot_id,
                "status": "done",
                "external_id": previous["external_id"] if previous else None,
                "already_published": True,
            }

        variant = conn.execute(
            "SELECT * FROM variants WHERE id = ?", (slot["variant_id"],)
        ).fetchone()
        if variant["status"] != "approved":
            raise PublishError(
                409, f"Variant is {variant['status']}; only approved variants can be published."
            )
        publisher = get_publisher(variant["platform"])

    # Layer 2: the adapter dedupes on the idempotency key.
    result = publisher.publish(variant["text"], slot["idempotency_key"])

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO publish_attempts (slot_id, adapter, result, detail, external_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (slot_id, publisher.name, "success" if result.ok else "failure",
             result.detail, result.external_id),
        )
        if result.ok:
            conn.execute("UPDATE slots SET status = 'done' WHERE id = ?", (slot_id,))
            conn.execute("UPDATE variants SET status = 'published' WHERE id = ?", (variant["id"],))
        else:
            conn.execute("UPDATE slots SET status = 'failed' WHERE id = ?", (slot_id,))

    return {
        "slot_id": slot_id,
        "status": "done" if result.ok else "failed",
        "adapter": publisher.name,
        "external_id": result.external_id,
        "already_published": False,
    }