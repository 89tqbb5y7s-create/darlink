#!/usr/bin/env python3
"""Fast v4: skip missing Wikisource HTML pages immediately."""
from __future__ import annotations

import re
import shutil
import time
from urllib.parse import quote

from bs4 import BeautifulSoup

import build_corpus_2013_v2 as base
import build_corpus_2013_v3 as v3


def quick_direct_wikisource_text(query: str) -> tuple[str, str]:
    page_url = "https://zh.wikisource.org/zh-hans/" + quote(query.replace(" ", "_"), safe="/:()（）")
    for attempt in range(4):
        response = base.SESSION.get(page_url, timeout=35)
        if response.status_code == 404:
            return page_url, ""
        if response.status_code == 429:
            time.sleep(5 + attempt * 5)
            continue
        if response.status_code >= 500:
            time.sleep(2 + attempt * 3)
            continue
        response.raise_for_status()
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
    return page_url, ""


v3.direct_wikisource_text = quick_direct_wikisource_text


def main() -> None:
    shutil.rmtree(base.OUT, ignore_errors=True)
    pool: list[dict] = []
    v3.collect_official_html(pool)
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
