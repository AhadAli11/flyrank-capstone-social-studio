import httpx
from bs4 import BeautifulSoup


def from_markdown(markdown: str) -> tuple[str, str]:
    title = "Untitled"
    for line in markdown.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    return title, markdown.strip()


def from_url(url: str) -> tuple[str, str]:
    response = httpx.get(url, timeout=10, follow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    title = url
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    body = "\n\n".join(p for p in paragraphs if p)
    return title, body