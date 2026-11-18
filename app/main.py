import sqlite3

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app import ingest
from app.db import get_conn, init_db
from app.generator import generate_variant
from app.profiles import PLATFORMS
from app.validation import validate
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