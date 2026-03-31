#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = ROOT / "pages"

TABLE_LINK_RE = re.compile(
    r'(<a class="table-link" href="(?P<href>[^"]+)">)(?P<body>.*?)(</a>)',
    re.S,
)
IMG_RE = re.compile(r'<img class="content-image" src="([^"]+)"')
ANY_IMG_RE = re.compile(r'<img[^>]+src="([^"]+)"')
HEADING_RE = re.compile(r'<h[234] id="(?P<id>[^"]+)"[^>]*>')


def build_preview_map() -> dict[str, str]:
    previews: dict[str, str] = {}
    for path in PAGES_DIR.glob("*.html"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        match = IMG_RE.search(text) or ANY_IMG_RE.search(text)
        if match:
            previews[path.name] = match.group(1)
    return previews


def current_page_preview(current_path: Path, previews: dict[str, str]) -> str | None:
    return previews.get(current_path.name)


def preview_for_href(current_path: Path, href: str, previews: dict[str, str]) -> str | None:
    fallback = current_page_preview(current_path, previews)
    if href.startswith("./"):
        return previews.get(href[2:]) or fallback
    if href.startswith("https://game8.jp/pocoapokemon/"):
        page_id = href.rsplit("/", 1)[-1]
        return previews.get(f"{page_id}.html") or fallback
    if href.startswith("#"):
        text = current_path.read_text(encoding="utf-8", errors="ignore")
        pos = text.find(f'id="{href[1:]}"')
        if pos == -1:
            return fallback
        heading = HEADING_RE.search(text, pos=pos)
        if not heading:
            return fallback
        img = IMG_RE.search(text, pos=heading.end())
        return img.group(1) if img else fallback
    return fallback


def ensure_css(text: str) -> str:
    if ".table-thumb {" in text:
        return text
    marker = """      .table-link small {\n        color: #87928d;\n      }\n"""
    addition = """      .table-link small {\n        color: #87928d;\n      }\n      .table-thumb {\n        display: block;\n        width: 100%;\n        aspect-ratio: 16 / 9;\n        object-fit: cover;\n        border: 1px solid #ececec;\n        background: #fafafa;\n      }\n"""
    return text.replace(marker, addition)


def enrich_file(path: Path, previews: dict[str, str]) -> bool:
    original = path.read_text(encoding="utf-8", errors="ignore")
    text = ensure_css(original)

    def repl(match: re.Match[str]) -> str:
        body = match.group("body")
        if 'class="table-thumb"' in body:
            return match.group(0)
        preview = preview_for_href(path, match.group("href"), previews)
        if not preview:
            return match.group(0)
        img = f'\n                    <img class="table-thumb" src="{preview}" loading="lazy" alt="条目预览图" />'
        return f"{match.group(1)}{img}{body}{match.group(4)}"

    enriched = TABLE_LINK_RE.sub(repl, text)
    if enriched != original:
        path.write_text(enriched, encoding="utf-8")
        return True
    return False


def main() -> int:
    previews = build_preview_map()
    targets = [Path(arg).resolve() for arg in sys.argv[1:]] if len(sys.argv) > 1 else sorted(PAGES_DIR.glob("*.html"))
    changed = 0
    for target in targets:
        if enrich_file(target, previews):
            changed += 1
    print(f"updated={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
