# ABOUTME: Fetch arbitrary web content and turn it into a podcast.
# ABOUTME: Demonstrates the "feed me anything" shape — URL → readable text → MP3.

"""Fetch a URL, extract readable text, generate a podcast about it.

Requires: `pip install httpx readability-lxml lxml_html_clean`.
Demonstrates that the library accepts any source material — not just
structured documents. Drop in any extractor (Tavily, Trafilatura,
Newspaper3k, your own scraper) the same way.

Usage:
    export GEMINI_API_KEY=...
    uv run python examples/from_url.py https://example.com/article
"""

import sys

import httpx
from readability import Document  # type: ignore

from gemini_podcast import PodcastConfig, Section, generate_podcast


def fetch_article(url: str) -> tuple[str, str]:
    html = httpx.get(url, follow_redirects=True, timeout=20).text
    doc = Document(html)
    return doc.title(), doc.summary()


def main(url: str) -> None:
    title, body_html = fetch_article(url)
    print(f"Fetched: {title}")

    result = generate_podcast(
        subject=title,
        sections=[Section(title="Article", content=body_html)],
        config=PodcastConfig(
            host_a_name="Alex",
            host_b_name="Maya",
            host_a_voice="Kore",
            host_b_voice="Sulafat",
            persona_hint="two curious analysts breaking down what the piece actually claims",
        ),
    )

    out = "url.mp3"
    with open(out, "wb") as f:
        f.write(result.mp3_bytes)
    print(f"Wrote {out} ({len(result.mp3_bytes):,} bytes)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python examples/from_url.py <url>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
