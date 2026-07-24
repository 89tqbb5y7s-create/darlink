#!/usr/bin/env python3
"""Fast HTML-only official-document collector using the v2 cleaning/QA pipeline."""
from __future__ import annotations

import re
import shutil
import time
from urllib.parse import quote

from bs4 import BeautifulSoup

import build_corpus_2013_v2 as base


def direct_wikisource_text(query: str) -> tuple[str, str]:
    page_url = "https://zh.wikisource.org/zh-hans/" + quote(query.replace(" ", "_"), safe="/:()（）")
    response = base.fetch(page_url)
    soup = BeautifulSoup(response.text, "lxml")
    container = soup.select_one("#mw-content-text .mw-parser-output, .mw-parser-output")
    if not container or container.select_one(".noarticletext"):
        return page_url, ""
    base.drop_nonbody(container)
    lines: list[str] = []
    started = False
    for element in container.find_all(["h2", "h3", "h4", "p", "li"]):
        value = base.CC.convert(element.get_text(" ", strip=True))
        if base.STOP.fullmatch(value):
            break
        if not started:
            started = bool(re.search(r"各位代表|前\s*言|过去五年|工作回顾|当前|一、|第一", value) or len(value) > 90)
            if not started:
                continue
        lines.append(value)
    return page_url, base.clean_lines(lines)


def collect_official_html(pool: list[dict]) -> None:
    documents = base.OFFICIAL_DOCS + [
        (query, author, "地方治理回顾 / 政策展望", official_url)
        for query, author, official_url in base.REGIONAL_DOCS
    ]
    aliases = {
        "2013年北京市政府工作报告": ["2013年北京市人民政府工作报告"],
        "2013年上海市政府工作报告": ["2013年上海市人民政府工作报告"],
        "2013年天津市政府工作报告": ["2013年天津市人民政府工作报告"],
        "2013年重庆市政府工作报告": ["2013年重庆市人民政府工作报告"],
        "2013年广东省政府工作报告": ["2013年广东省人民政府工作报告"],
        "2013年浙江省政府工作报告": ["2013年浙江省人民政府工作报告"],
        "2013年江苏省政府工作报告": ["2013年江苏省人民政府工作报告"],
        "2013年山东省政府工作报告": ["2013年山东省人民政府工作报告"],
        "2013年河南省政府工作报告": ["2013年河南省人民政府工作报告"],
        "2013年湖北省政府工作报告": ["2013年湖北省人民政府工作报告"],
        "2013年湖南省政府工作报告": ["2013年湖南省人民政府工作报告"],
        "2013年四川省政府工作报告": ["2013年四川省人民政府工作报告"],
        "2013年福建省政府工作报告": ["2013年福建省人民政府工作报告"],
        "2013年安徽省政府工作报告": ["2013年安徽省人民政府工作报告"],
        "2013年河北省政府工作报告": ["2013年河北省人民政府工作报告"],
        "2013年辽宁省政府工作报告": ["2013年辽宁省人民政府工作报告"],
        "2013年陕西省政府工作报告": ["2013年陕西省人民政府工作报告"],
        "2013年云南省政府工作报告": ["2013年云南省人民政府工作报告"],
        "2013年广西壮族自治区政府工作报告": ["2013年广西壮族自治区人民政府工作报告"],
        "2013年内蒙古自治区政府工作报告": ["2013年内蒙古自治区人民政府工作报告"],
    }
    for query, author, genre, official_url in documents:
        candidates = [query] + aliases.get(query, [])
        selected_url = ""
        selected_text = ""
        selected_title = query
        for candidate in candidates:
            try:
                selected_url, selected_text = direct_wikisource_text(candidate)
                if base.non_ws(selected_text) >= 700:
                    selected_title = candidate
                    break
            except Exception as exc:
                print("DIRECT_FAIL", candidate, exc)
            time.sleep(0.4)
        if base.non_ws(selected_text) < 700:
            print("DIRECT_NOT_FOUND", query)
            continue
        base.add_text(
            pool,
            title=query,
            author=author,
            date="2013",
            source_url=selected_url,
            official_url=official_url,
            platform="Wikisource HTML / 国家机关公开文件",
            genre="state official document / " + genre,
            rights=base.PUBLIC_LICENSE,
            license_url=base.PUBLIC_LICENSE_URL,
            text=selected_text,
            notes=f"official_url={official_url}; Wikisource HTML page={selected_title}; main body only; Simplified Chinese conversion.",
        )
        print("DIRECT_OFFICIAL", query, base.non_ws(selected_text))


def main() -> None:
    shutil.rmtree(base.OUT, ignore_errors=True)
    pool: list[dict] = []
    collect_official_html(pool)
    base.collect_ruanyf(pool)
    base.collect_coolshell(pool)
    total = sum(item["char_count"] for item in pool)
    print("POOL", len(pool), total, sorted({item["source_platform"] for item in pool}))
    if total < 225_000:
        raise SystemExit(f"insufficient pool: {total}")
    bins, unused = base.select_bins(pool)
    print("BIN_RAW", [sum(item["char_count"] for item in selected) for selected in bins])
    base.write_outputs(bins, unused)


if __name__ == "__main__":
    main()
