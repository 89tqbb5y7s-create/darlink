#!/usr/bin/env python3
"""Add CC BY-SA 4.0 Pingmin 2013 posts to the fixed-snapshot corpus."""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup

import build_corpus_2013_v5 as base
import build_corpus_2013_v7 as v7
import build_corpus_2013_v8 as v8

PINGMIN_REPO = "https://github.com/Pingmin/blog.git"
PINGMIN_COMMIT = "ff167955ce3e301b0e20dbff146e4a3768394d66"
PINGMIN_POSTS = [
    ("post/the-donation-details-for-a-primary-school.html", "2013-01-05", "公益活动回顾 / 社会评论"),
    ("post/loving-our-greater-china.html", "2013-10-04", "政治与社会观点 / 历史评论"),
    ("post/she.html", "2013-11-24", "个人随笔 / 情感评论"),
]


def collect_pingmin(pool: list[dict], repo: Path) -> None:
    accepted = 0
    for relative, date, genre in PINGMIN_POSTS:
        path = repo / relative
        if not path.exists():
            continue
        soup = BeautifulSoup(path.read_text("utf-8", errors="ignore"), "lxml")
        title_node = soup.select_one("h1.post-title, .post-title")
        body = soup.select_one(".post-body")
        if not title_node or not body:
            continue
        for selector in "script style noscript img svg figure figcaption table pre code blockquote .post-meta .post-footer .comments .related".split():
            for node in body.select(selector):
                node.decompose()
        title = base.CC.convert(title_node.get_text(" ", strip=True))
        lines = [element.get_text(" ", strip=True) for element in body.find_all(["h2", "h3", "h4", "p", "li"])]
        text = base.clean_paragraphs(lines)
        official = "https://pingmin.github.io/blog/" + relative
        source = (
            "https://github.com/Pingmin/blog/blob/"
            f"{PINGMIN_COMMIT}/" + quote(relative, safe="/")
        )
        base.add(
            pool,
            title=title,
            author="平民（Pingmin Fenlly Liu）",
            date=date,
            source_url=source,
            official_url=official,
            platform="平民博客固定仓库快照",
            genre=genre,
            rights="CC BY-SA 4.0",
            license_url="https://creativecommons.org/licenses/by-sa/4.0/",
            text=text,
            notes=(
                f"Fixed repository commit; official_url={official}; site displays CC BY-SA 4.0; "
                "title/date metadata, images, captions, quotations, navigation and footer removed; "
                "Traditional characters converted to Simplified Chinese."
            ),
        )
        accepted += 1
    print("PINGMIN", accepted)


def main() -> None:
    shutil.rmtree(base.OUT, ignore_errors=True)
    root = Path("/tmp/corpus2013_sources")
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    ruanyf = root / "read"
    coolshell = root / "haoel"
    gov = root / "gov"
    yihui = root / "yihui"
    govdata = root / "govdata"
    pingmin = root / "pingmin"
    base.clone_at(base.RUANYF_REPO, base.RUANYF_COMMIT, ruanyf)
    base.clone_at(base.COOLSHELL_REPO, base.COOLSHELL_COMMIT, coolshell)
    base.clone_at(base.GOV_REPO, base.GOV_COMMIT, gov)
    base.clone_at(v8.YIHUI_REPO, v8.YIHUI_COMMIT, yihui)
    base.clone_at(v8.GOVDATA_REPO, v8.GOVDATA_COMMIT, govdata)
    base.clone_at(PINGMIN_REPO, PINGMIN_COMMIT, pingmin)
    pool: list[dict] = []
    v7.collect_all_chinese_ruanyf(pool, ruanyf)
    base.collect_coolshell(pool, coolshell)
    base.collect_government(pool, gov)
    v8.collect_yihui(pool, yihui)
    v8.collect_government_dataset(pool, govdata)
    collect_pingmin(pool, pingmin)
    total = sum(item["char_count"] for item in pool)
    print("POOL", len(pool), total, sorted({item["source_platform"] for item in pool}))
    if total < 225_000:
        raise SystemExit(f"insufficient pool: {total}")
    bins, unused = base.choose_bins(pool)
    print("BIN_RAW", [sum(item["char_count"] for item in selected) for selected in bins])
    base.write_outputs(bins, unused)


if __name__ == "__main__":
    main()
