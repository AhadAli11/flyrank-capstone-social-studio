import sqlite3
from app.publish_service import PublishError, publish_slot

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app import ingest
from app.db import get_conn, init_db
from app.generator import generate_variant
from app.profiles import PLATFORMS
from app.validation import validate
from datetime import datetime, timezone

from fastapi.responses import JSONResponse

init_db()
app = FastAPI(title="Social Media Studio")


class PostIn(BaseModel):
    markdown: str | None = None
    url: str | None = None


@app.post("/posts", status_code=201)
def create_post(payload: PostIn):
    if bool(payload.markdown) == bool(payload.url):
        raise HTTPException(400, "Provide exactly one of 'markdown' or 'url'.")

    if payload.markdown:
        source_type, source_url = "markdown", None
        title, body = ingest.from_markdown(payload.markdown)
    else:
        source_type, source_url = "url", payload.url
        try:
            title, body = ingest.from_url(payload.url)
        except httpx.HTTPError as e:
            raise HTTPException(400, f"Could not fetch URL: {e}")

    if not body:
        raise HTTPException(400, "The post has no text content.")

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO posts (source_type, source_url, title, body) VALUES (?, ?, ?, ?)",
            (source_type, source_url, title, body),
        )
        post_id = cur.lastrowid

    return {"id": post_id, "title": title}


@app.get("/posts/{post_id}")
def get_post(post_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Post not found.")
    return dict(row)

class VariantEdit(BaseModel):
    text: str


@app.post("/posts/{post_id}/variants", status_code=201)
def create_variants(post_id: int):
    with get_conn() as conn:
        post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        if post is None:
            raise HTTPException(404, "Post not found.")

        for platform in PLATFORMS:
            text = generate_variant(platform, post["title"], post["body"])
            errors = validate(platform, text)
            if errors:
                raise HTTPException(500, f"Generated variant for {platform} is invalid: {errors}")
            try:
                conn.execute(
                    "INSERT INTO variants (post_id, platform, text) VALUES (?, ?, ?)",
                    (post_id, platform, text),
                )
            except sqlite3.IntegrityError:
                raise HTTPException(409, "Variants were already generated for this post.")

        rows = conn.execute("SELECT * FROM variants WHERE post_id = ?", (post_id,)).fetchall()
    return [dict(r) for r in rows]


@app.get("/posts/{post_id}/variants")
def list_variants(post_id: int):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM variants WHERE post_id = ?", (post_id,)).fetchall()
    return [dict(r) for r in rows]


@app.put("/variants/{variant_id}")
def edit_variant(variant_id: int, payload: VariantEdit):
    with get_conn() as conn:
        variant = conn.execute("SELECT * FROM variants WHERE id = ?", (variant_id,)).fetchone()
        if variant is None:
            raise HTTPException(404, "Variant not found.")
        if variant["status"] == "published":
            raise HTTPException(409, "A published variant cannot be edited.")

        errors = validate(variant["platform"], payload.text)
        if errors:
            raise HTTPException(422, {"message": "Variant breaks platform rules.", "errors": errors})

        conn.execute(
            "UPDATE variants SET text = ?, status = 'draft' WHERE id = ?",
            (payload.text, variant_id),
        )
        row = conn.execute("SELECT * FROM variants WHERE id = ?", (variant_id,)).fetchone()
    return dict(row)

class ScheduleIn(BaseModel):
    publish_at: datetime


def _get_variant(conn, variant_id: int):
    variant = conn.execute("SELECT * FROM variants WHERE id = ?", (variant_id,)).fetchone()
    if variant is None:
        raise HTTPException(404, "Variant not found.")
    return variant


@app.post("/variants/{variant_id}/approve")
def approve_variant(variant_id: int):
    with get_conn() as conn:
        variant = _get_variant(conn, variant_id)
        if variant["status"] != "draft":
            raise HTTPException(
                409, f"Only a draft variant can be approved (current status: {variant['status']})."
            )

        errors = validate(variant["platform"], variant["text"])
        if errors:
            raise HTTPException(422, {"message": "Variant breaks platform rules.", "errors": errors})

        conn.execute("UPDATE variants SET status = 'approved' WHERE id = ?", (variant_id,))
        row = _get_variant(conn, variant_id)
    return dict(row)


@app.post("/variants/{variant_id}/reject")
def reject_variant(variant_id: int):
    with get_conn() as conn:
        variant = _get_variant(conn, variant_id)
        if variant["status"] not in ("draft", "approved"):
            raise HTTPException(
                409, f"A {variant['status']} variant cannot be rejected."
            )
        conn.execute("UPDATE variants SET status = 'rejected' WHERE id = ?", (variant_id,))
        row = _get_variant(conn, variant_id)
    return dict(row)


@app.post("/variants/{variant_id}/schedule", status_code=201)
def schedule_variant(variant_id: int, payload: ScheduleIn):
    publish_at = payload.publish_at
    if publish_at.tzinfo is None:
        publish_at = publish_at.replace(tzinfo=timezone.utc)
    publish_at = publish_at.astimezone(timezone.utc)

    with get_conn() as conn:
        variant = _get_variant(conn, variant_id)
        if variant["status"] != "approved":
            raise HTTPException(
                409,
                f"Only an approved variant can be scheduled (current status: {variant['status']}).",
            )
        if publish_at <= datetime.now(timezone.utc):
            raise HTTPException(422, "publish_at must be in the future.")

        key = f"{variant_id}:{publish_at.isoformat()}"
        existing = conn.execute(
            "SELECT * FROM slots WHERE idempotency_key = ?", (key,)
        ).fetchone()
        if existing:
            return JSONResponse(dict(existing), status_code=200)

        cur = conn.execute(
            "INSERT INTO slots (variant_id, publish_at, idempotency_key) VALUES (?, ?, ?)",
            (variant_id, publish_at.isoformat(), key),
        )
        slot = conn.execute("SELECT * FROM slots WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(slot)

@app.post("/slots/{slot_id}/publish")
def publish_now(slot_id: int):
    try:
        return publish_slot(slot_id)
    except PublishError as e:
        raise HTTPException(e.status_code, e.message)


@app.get("/history")
def history():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM publish_attempts ORDER BY id").fetchall()
    return [dict(r) for r in rows]


@app.get("/mock-posts")
def mock_posts():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM mock_posts ORDER BY id").fetchall()
    return [dict(r) for r in rows]

