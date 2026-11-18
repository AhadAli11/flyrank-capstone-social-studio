import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app import ingest
from app.db import get_conn, init_db

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