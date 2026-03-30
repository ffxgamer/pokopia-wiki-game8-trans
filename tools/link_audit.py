#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = ROOT / "pages"
PAGES_JSON = ROOT / "pages.json"
BASE_URL = "https://game8.jp/pocoapokemon"

HREF_RE = re.compile(r'href="([^"]+)"')
ANCHOR_RE = re.compile(r'<a\b([^>]*)href="([^"]+)"([^>]*)>(.*?)</a>', re.S)
SIDE_LIST_RE = re.compile(r'(<ul class="side-list">)(.*?)(</ul>)', re.S)
LI_RE = re.compile(r'<li>.*?</li>', re.S)
HEADING_RE = re.compile(r'<h([1-6])[^>]*\sid="([^"]+)"[^>]*>(.*?)</h\1>', re.S)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
STRONG_EMPTY_RE = re.compile(r"^\s*<strong[^>]*>\s*</strong>\s*$", re.S)
TAG_RE = re.compile(r"<[^>]+>")
RUNTIME_ID_RE = re.compile(r'id:\s*"([^"]+)"')
GENERIC_ID_RE = re.compile(r'\sid="([^"]+)"')


def strip_tags(value: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub("", value)).strip()


def local_page_files() -> list[Path]:
    return sorted(PAGES_DIR.glob("*.html")) + [ROOT / "index.html"]


def load_pages_json_titles() -> dict[str, str]:
    data = json.loads(PAGES_JSON.read_text())
    return {entry["id"]: entry["title"] for entry in data}


def load_local_title_map() -> dict[str, str]:
    titles: dict[str, str] = {}
    for path in PAGES_DIR.glob("*.html"):
        match = TITLE_RE.search(path.read_text())
        if not match:
            continue
        titles[path.stem] = strip_tags(html.unescape(match.group(1)))
    return titles


def build_heading_map(text: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for _, anchor_id, inner in HEADING_RE.findall(text):
        label = strip_tags(html.unescape(inner))
        if label:
            mapping[anchor_id] = label
    return mapping


def ordered_heading_targets(text: str) -> list[tuple[str, str]]:
    headings: list[tuple[str, str, str]] = []
    for level, anchor_id, inner in HEADING_RE.findall(text):
        label = strip_tags(html.unescape(inner))
        if label:
            headings.append((level, anchor_id, label))

    if len(headings) <= 1:
        return [(anchor_id, label) for _, anchor_id, label in headings]

    # For legacy #hm_N anchors, the first heading is usually the page's root section.
    # The navigation tiles are meant to jump to the following subsection headings.
    section_like = [(anchor_id, label) for level, anchor_id, label in headings[1:] if level in {"2", "3", "4"}]
    return section_like or [(anchor_id, label) for _, anchor_id, label in headings]


def runtime_ids(text: str) -> set[str]:
    return set(RUNTIME_ID_RE.findall(text))


def document_ids(text: str) -> set[str]:
    return set(GENERIC_ID_RE.findall(text))


def resolve_legacy_hm_anchor(href: str, heading_targets: list[tuple[str, str]]) -> tuple[str, str] | None:
    match = re.fullmatch(r"#hm_(\d+)", href)
    if not match:
        return None
    number = int(match.group(1))
    if number >= 100:
        index = number - 101
    else:
        index = number - 1
    if 0 <= index < len(heading_targets):
        return heading_targets[index]
    return None


def resolve_local_target(current_file: Path, href: str) -> Path | None:
    if href.startswith("http://") or href.startswith("https://") or href.startswith("#"):
        return None
    return (current_file.parent / href).resolve()


def page_id_from_href(href: str) -> str | None:
    match = re.search(r"(\d+)\.html$", href)
    return match.group(1) if match else None


def replacement_label(
    href: str,
    heading_map: dict[str, str],
    heading_targets: list[tuple[str, str]],
    pages_titles: dict[str, str],
    local_titles: dict[str, str],
) -> str | None:
    if href.startswith("#"):
        if href == "#url":
            return "查看原文"
        legacy = resolve_legacy_hm_anchor(href, heading_targets)
        if legacy:
            return legacy[1]
        return heading_map.get(href[1:])
    page_id = page_id_from_href(href)
    if not page_id:
        return None
    return pages_titles.get(page_id) or local_titles.get(page_id) or f"查看原文 {page_id}"


def replace_anchor_inner(anchor_html: str, new_label: str) -> str:
    escaped = html.escape(new_label)
    match = ANCHOR_RE.fullmatch(anchor_html)
    if not match:
        return anchor_html
    prefix1, href, prefix2, inner = match.groups()
    if STRONG_EMPTY_RE.match(inner):
        inner = re.sub(
            r"(<strong[^>]*>)\s*(</strong>)",
            rf"\1{escaped}\2",
            inner,
            count=1,
            flags=re.S,
        )
    else:
        inner = escaped
    return f'<a{prefix1}href="{href}"{prefix2}>{inner}</a>'


def replace_anchor_href(anchor_html: str, new_href: str) -> str:
    return re.sub(r'href="[^"]+"', f'href="{html.escape(new_href)}"', anchor_html, count=1)


def fix_side_list_block(
    block_html: str,
    heading_map: dict[str, str],
    stats: Counter,
) -> str:
    start, body, end = SIDE_LIST_RE.fullmatch(block_html).groups()
    new_items: list[str] = []
    for li_html in LI_RE.findall(body):
        anchor_match = re.search(r'<a\b[^>]*href="(#.*?)"[^>]*>(.*?)</a>', li_html, re.S)
        if not anchor_match:
            new_items.append(li_html)
            continue
        href, inner = anchor_match.groups()
        anchor_id = href[1:]
        label = strip_tags(inner)
        if anchor_id not in heading_map:
            stats["removed_invalid_sidebar_anchor"] += 1
            continue
        if not label:
            replacement = replace_anchor_inner(anchor_match.group(0), heading_map[anchor_id])
            li_html = li_html.replace(anchor_match.group(0), replacement, 1)
            stats["filled_empty_sidebar_anchor_text"] += 1
        new_items.append(li_html)
    return f"{start}{''.join(new_items)}{end}"


def fix_file(
    path: Path,
    pages_titles: dict[str, str],
    local_titles: dict[str, str],
) -> tuple[str, Counter]:
    text = path.read_text()
    stats: Counter = Counter()
    heading_map = build_heading_map(text)
    heading_targets = ordered_heading_targets(text)

    def side_list_replacer(match: re.Match[str]) -> str:
        return fix_side_list_block(match.group(0), heading_map, stats)

    text = SIDE_LIST_RE.sub(side_list_replacer, text)

    def anchor_replacer(match: re.Match[str]) -> str:
        full = match.group(0)
        href = match.group(2)
        inner = match.group(4)
        visible = strip_tags(inner)

        if href.startswith("#") and href[1:] not in heading_map:
            if href == "#url" and path.name != "index.html":
                full = replace_anchor_href(full, f"{BASE_URL}/{path.stem}")
                stats["rewrote_placeholder_url_anchor"] += 1
                if not visible:
                    full = replace_anchor_inner(full, "查看原文")
                    stats["filled_empty_link_text"] += 1
                return full
            legacy = resolve_legacy_hm_anchor(href, heading_targets)
            if legacy:
                target_id, target_label = legacy
                full = replace_anchor_href(full, f"#{target_id}")
                stats["rewrote_legacy_hm_anchor"] += 1
                if not visible:
                    full = replace_anchor_inner(full, target_label)
                    stats["filled_empty_link_text"] += 1
                return full
            return full

        target = resolve_local_target(path, href)
        page_id = page_id_from_href(href)

        if target is not None and not target.exists() and page_id:
            full = replace_anchor_href(full, f"{BASE_URL}/{page_id}")
            stats["rewrote_missing_local_link_to_source"] += 1

        if not visible:
            new_label = replacement_label(href, heading_map, heading_targets, pages_titles, local_titles)
            if new_label:
                full = replace_anchor_inner(full, new_label)
                stats["filled_empty_link_text"] += 1
        return full

    text = ANCHOR_RE.sub(anchor_replacer, text)
    return text, stats


def audit_file(path: Path) -> Counter:
    text = path.read_text()
    heading_map = build_heading_map(text)
    valid_ids = set(heading_map) | runtime_ids(text) | document_ids(text)
    counts: Counter = Counter()

    for href in HREF_RE.findall(text):
        if href.startswith("./") or href.startswith("../") or href.startswith("pages/"):
            target = resolve_local_target(path, href)
            if target is not None and not target.exists():
                counts["missing_targets"] += 1
        elif href.startswith("#") and href[1:] not in valid_ids:
            counts["missing_anchors"] += 1

    for href, inner in re.findall(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', text, re.S):
        if not strip_tags(inner):
            counts["empty_text_links"] += 1

    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="Apply safe link fixes in place.")
    parser.add_argument(
        "--limit",
        nargs="*",
        default=[],
        help="Optional subset of filenames to process, e.g. 767406.html index.html",
    )
    args = parser.parse_args()

    files = local_page_files()
    if args.limit:
        wanted = set(args.limit)
        files = [path for path in files if path.name in wanted]

    pages_titles = load_pages_json_titles()
    local_titles = load_local_title_map()

    if args.fix:
        total_fix_stats: Counter = Counter()
        for path in files:
            new_text, stats = fix_file(path, pages_titles, local_titles)
            if stats:
                path.write_text(new_text)
                total_fix_stats.update(stats)
        print(json.dumps(total_fix_stats, ensure_ascii=False, indent=2, sort_keys=True))
        return

    totals: Counter = Counter()
    for path in files:
        totals.update(audit_file(path))
    print(json.dumps(totals, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
