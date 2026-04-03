#!/usr/bin/env python3
from __future__ import annotations

import re
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / "pages"

TYPE_PAGES = {
    "769332": {
        "type_name": "一般属性",
        "jp_anchor": "ノーマルタイプの宝可梦一览",
    },
    "769331": {
        "type_name": "火属性",
        "jp_anchor": "ほのおタイプの宝可梦一览",
    },
    "769330": {
        "type_name": "水属性",
        "jp_anchor": "みずタイプの宝可梦一览",
    },
    "769328": {
        "type_name": "电属性",
        "jp_anchor": "でんきタイプの宝可梦一览",
    },
    "769315": {
        "type_name": "妖精属性",
        "jp_anchor": "フェアリータイプの宝可梦一览",
    },
}

LOCAL_TITLE_OVERRIDES = {
    "768261.html": "爆炸效果与对应宝可梦一览",
    "768262.html": "工匠效果与对应宝可梦一览",
    "768354.html": "稀有物品效果与对应宝可梦一览",
}

SKILL_PAGES = {
    "768261": {
        "page_title": "爆炸效果与对应宝可梦一览",
        "meta_description": "爆炸效果说明与对应宝可梦一览。",
        "lead": "本文整理了《Pokémon Pokopia》的爆炸效果与对应宝可梦，并附上出现地图、栖息地与所需条件。",
        "short_lead": "这里汇总了《Pokémon Pokopia》中擅长爆炸效果的宝可梦与相关条件。",
        "section_title": "爆炸效果",
        "section_text": "擅长爆炸效果的宝可梦可以炸飞周围物体并破坏障碍。",
        "table_title": "擅长爆炸效果的宝可梦",
    },
    "768262": {
        "page_title": "工匠效果与对应宝可梦一览",
        "meta_description": "工匠效果说明与对应宝可梦一览。",
        "lead": "本文整理了《Pokémon Pokopia》的工匠效果与对应宝可梦，并附上出现地图、栖息地与所需条件。",
        "short_lead": "这里汇总了《Pokémon Pokopia》中擅长工匠效果的宝可梦与相关条件。",
        "section_title": "工匠效果",
        "section_text": "擅长工匠效果的宝可梦可以协助大型建筑与设施施工。",
        "table_title": "擅长工匠效果的宝可梦",
    },
    "768354": {
        "page_title": "稀有物品效果与对应宝可梦一览",
        "meta_description": "稀有物品效果说明与对应宝可梦一览。",
        "lead": "本文整理了《Pokémon Pokopia》的稀有物品效果与对应宝可梦，并附上出现地图、栖息地与所需条件。",
        "short_lead": "这里汇总了《Pokémon Pokopia》中擅长寻找稀有物品的宝可梦与相关条件。",
        "section_title": "稀有物品效果",
        "section_text": "擅长稀有物品效果的宝可梦更容易帮你找到珍贵道具。",
        "table_title": "擅长稀有物品效果的宝可梦",
    },
}


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def extract_local_titles() -> dict[str, str]:
    titles: dict[str, str] = {}
    for path in PAGES_DIR.glob("*.html"):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"<title>(.*?)</title>", text, flags=re.S)
        if not match:
            continue
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        titles[path.name] = title
    titles.update(LOCAL_TITLE_OVERRIDES)
    return titles


def extract_remote_names(source_html: str) -> dict[str, str]:
    names: dict[str, str] = {}
    for match in re.finditer(
        r'<a class="a-link" href="https://game8\.jp/pocoapokemon/(\d+)">([^<]+)</a>',
        source_html,
    ):
        pid, label = match.groups()
        clean = label.strip()
        if not clean:
            continue
        # Keep the first useful visible name; later rows repeat skill links.
        names.setdefault(pid, clean)
    return names


def replace_strong_link_labels(html: str, label_map: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        href = match.group(1)
        label = match.group(2)

        page_match = re.search(r"\./(\d+\.html)", href)
        if page_match:
            key = page_match.group(1)
            if key in label_map:
                return f'<a class="table-link" href="{href}"><strong>{label_map[key]}</strong></a>'
            return match.group(0)

        remote_match = re.search(r"game8\.jp/pocoapokemon/(\d+)", href)
        if remote_match:
            key = remote_match.group(1)
            if key in label_map:
                return f'<a class="table-link" href="{href}"><strong>{label_map[key]}</strong></a>'
            return match.group(0)

        return match.group(0)

    return re.sub(
        r'<a class="table-link" href="([^"]+)">\s*<strong>(.*?)</strong>\s*</a>',
        repl,
        html,
        flags=re.S,
    )


def fix_page(page_id: str, config: dict[str, str], local_titles: dict[str, str]) -> None:
    page_path = PAGES_DIR / f"{page_id}.html"
    html = page_path.read_text(encoding="utf-8")
    source_html = fetch(f"https://game8.jp/pocoapokemon/{page_id}")

    remote_names = extract_remote_names(source_html)
    label_map = dict(local_titles)
    label_map.update(remote_names)

    html = replace_strong_link_labels(html, label_map)

    type_name = config["type_name"]
    jp_anchor = config["jp_anchor"]
    lead = (
        f"本文整理了《Pokémon Pokopia》的{type_name}宝可梦图鉴，"
        "收录各宝可梦的擅长工作、出现地点和栖息地条件。"
    )
    short_lead = (
        f"这里汇总了《Pokémon Pokopia》的{type_name}宝可梦，"
        "并附上擅长工作与栖息地信息。"
    )

    replacements = {
        "《Pokémon Pokopia》宝可梦一览。宝可梦得意栖息地詳掲載。 宝可梦宝可梦想了解的话可以参考本文": lead,
        "《Pokémon Pokopia》，宝可梦一览。宝可梦得意栖息地詳掲載。 宝可梦宝可梦想了解的话可以参考本文": lead,
        "《Pokémon Pokopia》宝可梦一览。宝可梦得意栖息地詳掲載": short_lead,
        "《Pokémon Pokopia》，宝可梦一览。宝可梦得意栖息地詳掲載": short_lead,
        '<meta name="description" content="查看原文清单、数据表与收集目标。" />': f'<meta name="description" content="{type_name}宝可梦图鉴、数据表与收集条件汇总。" />',
        f'<li><a href="#{jp_anchor}">宝可梦一览</a></li>': f'<li><a href="#{jp_anchor}">{type_name}宝可梦列表</a></li>',
        f'<h2 id="{jp_anchor}" class="content-head level-2">宝可梦一览</h2>': f'<h2 id="{jp_anchor}" class="content-head level-2">{type_name}宝可梦列表</h2>',
    }
    for old, new in replacements.items():
        html = html.replace(old, new)

    page_path.write_text(html, encoding="utf-8")


def fix_main_pokedex_page() -> None:
    page_path = PAGES_DIR / "767402.html"
    html = page_path.read_text(encoding="utf-8")
    replacements = {
        '<h3 id="ピカチュウ-うすいろ" class="content-head level-3"></h3>': '<h3 id="ピカチュウ-うすいろ" class="content-head level-3">浅色皮卡丘</h3>',
        '<h3 id="カビゴン-こけむし" class="content-head level-3"></h3>': '<h3 id="カビゴン-こけむし" class="content-head level-3">苔藓卡比兽</h3>',
        '<h3 id="ドーブル-ペインター" class="content-head level-3"></h3>': '<h3 id="ドーブル-ペインター" class="content-head level-3">画家图图犬</h3>',
        '<h3 id="ヨクバリス-コック" class="content-head level-3"></h3>': '<h3 id="ヨクバリス-コック" class="content-head level-3">厨师贪心栗鼠</h3>',
        '<h3 id="ステレオロトム" class="content-head level-3"></h3>': '<h3 id="ステレオロトム" class="content-head level-3">音响洛托姆</h3>',
        "城镇剧情中登場宝可梦，家具": "它会在城镇剧情中登场，和家具制作相关。",
        "城镇剧情中登場宝可梦，CD渡音游玩BGM": "它会在城镇剧情中登场，能帮你播放 CD 并更换背景音乐。",
    }
    for old, new in replacements.items():
        html = html.replace(old, new)
    page_path.write_text(html, encoding="utf-8")


def fix_skill_pages() -> None:
    local_titles = extract_local_titles()
    for page_id, config in SKILL_PAGES.items():
        page_name = f"{page_id}.html"
        page_path = PAGES_DIR / page_name
        html = page_path.read_text(encoding="utf-8")
        source_html = fetch(f"https://game8.jp/pocoapokemon/{page_id}")
        label_map = dict(local_titles)
        label_map.update(extract_remote_names(source_html))
        html = replace_strong_link_labels(html, label_map)

        replacements = {
            "<title>效果宝可梦一览</title>": f"<title>{config['page_title']}</title>",
            '<meta name="description" content="查看原文清单、数据表与收集目标。" />': f'<meta name="description" content="{config["meta_description"]}" />',
            "<h1>效果宝可梦一览</h1>": f"<h1>{config['page_title']}</h1>",
            '<p class="sub-title">效果宝可梦一览</p>': f'<p class="sub-title">{config["page_title"]}</p>',
            "Pokopia(Pokémon Pokopia)效果宝可梦一览。Pokopia登場得意宝可梦出現地图栖息地，必要詳掲載。 宝可梦想了解的话可以参考本文": config["lead"],
            "Pokopia(Pokémon Pokopia)效果宝可梦一览。Pokopia登場得意宝可梦出現地图栖息地，必要詳掲載": config["short_lead"],
            '<h2 id="ばくはつの效果" class="content-head level-2">效果</h2>': f'<h2 id="ばくはつの效果" class="content-head level-2">{config["section_title"]}</h2>',
            '<h2 id="しょくにんの效果" class="content-head level-2">效果</h2>': f'<h2 id="しょくにんの效果" class="content-head level-2">{config["section_title"]}</h2>',
            '<h2 id="レアものの效果" class="content-head level-2">效果</h2>': f'<h2 id="レアものの效果" class="content-head level-2">{config["section_title"]}</h2>',
            "<p>得意宝可梦飛爆発辺壊</p>": f"<p>{config['section_text']}</p>",
            "<p>得意巨大建物</p>": f"<p>{config['section_text']}</p>",
            "<p>得意宝可梦</p>": f"<p>{config['section_text']}</p>",
            '<h2 id="ばくはつが得意な宝可梦一览" class="content-head level-2">得意宝可梦一览</h2>': f'<h2 id="ばくはつが得意な宝可梦一览" class="content-head level-2">{config["table_title"]}</h2>',
            '<h2 id="しょくにんが得意な宝可梦一览" class="content-head level-2">得意宝可梦一览</h2>': f'<h2 id="しょくにんが得意な宝可梦一览" class="content-head level-2">{config["table_title"]}</h2>',
            '<h2 id="レアものが得意な宝可梦一览" class="content-head level-2">得意宝可梦一览</h2>': f'<h2 id="レアものが得意な宝可梦一览" class="content-head level-2">{config["table_title"]}</h2>',
            f'<li><a href="#ばくはつが得意な宝可梦一览">{config["section_text"]}一览</a></li>': '<li><a href="#ばくはつが得意な宝可梦一览">擅长爆炸效果的宝可梦</a></li>',
            f'<li><a href="#しょくにんが得意な宝可梦一览">{config["section_text"]}一览</a></li>': '<li><a href="#しょくにんが得意な宝可梦一览">擅长工匠效果的宝可梦</a></li>',
            f'<li><a href="#レアものが得意な宝可梦一览">{config["section_text"]}一览</a></li>': '<li><a href="#レアものが得意な宝可梦一览">擅长稀有物品效果的宝可梦</a></li>',
            f'<h2 id="しょくにんが得意な宝可梦一览" class="content-head level-2">{config["section_text"]}一览</h2>': '<h2 id="しょくにんが得意な宝可梦一览" class="content-head level-2">擅长工匠效果的宝可梦</h2>',
            f'<h2 id="レアものが得意な宝可梦一览" class="content-head level-2">{config["section_text"]}一览</h2>': '<h2 id="レアものが得意な宝可梦一览" class="content-head level-2">擅长稀有物品效果的宝可梦</h2>',
            f'<h2 id="ばくはつが得意な宝可梦一览" class="content-head level-2">{config["section_text"]}一览</h2>': '<h2 id="ばくはつが得意な宝可梦一览" class="content-head level-2">擅长爆炸效果的宝可梦</h2>',
        }
        for old, new in replacements.items():
            html = html.replace(old, new)
        page_path.write_text(html, encoding="utf-8")


def main() -> None:
    local_titles = extract_local_titles()
    fix_skill_pages()
    for page_id, config in TYPE_PAGES.items():
        fix_page(page_id, config, local_titles)
    fix_main_pokedex_page()


if __name__ == "__main__":
    main()
