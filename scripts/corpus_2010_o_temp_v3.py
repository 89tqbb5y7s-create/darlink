#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

from corpus_2010_o_temp import SOURCE_REPO, clean_rst, count_chars, dedupe_candidates, opinion_score, topic_of
from corpus_2010_o_temp_v2 import gather_coolshell_broad, write_outputs_v2
from corpus_2010_o_temp import choose_balanced


def make_item(path: Path, source_site: str, author: str, copyright_status: str,
              license_url: str, note: str, min_score: float = -3.0):
    raw = path.read_text(encoding="utf-8", errors="ignore")
    title, _, official, body = clean_rst(raw)
    if not title or not official or count_chars(body) < 600:
        return None
    score = opinion_score(title, body, str(path))
    if score < min_score:
        return None
    return {
        "title": title,
        "author": author,
        "official_url": official.replace("http://", "https://"),
        "mirror_source": f"https://github.com/me115/read/blob/master/{path.relative_to(SOURCE_REPO).as_posix()}",
        "source_site": source_site,
        "body": body,
        "char_count": count_chars(body),
        "topic": topic_of(title, body),
        "quality_score": round(score, 2),
        "copyright_status": copyright_status,
        "license_url": license_url,
        "notes": note,
    }


RUAN_EXCLUDE = re.compile(r"捐款|救救|征集|广告|地图|书摘|黑客英雄|判决书|遗书|软件下载|教程|代码|算法|函数|语法|安装|配置", re.I)
RUAN_TRANSLATION = re.compile(r"译文|翻译|译者|文章来源")


def gather_ruan_dynamic():
    items = []
    seen = set()
    roots = [
        SOURCE_REPO / "ruanyifeng" / "opinions",
        SOURCE_REPO / "ruanyifeng" / "essays",
        SOURCE_REPO / "ruanyifeng" / "sci-tech",
        SOURCE_REPO / "ruanyifeng" / "misc",
    ]
    for root in roots:
        if not root.exists():
            continue
        for path in root.glob("*.rst"):
            raw = path.read_text(encoding="utf-8", errors="ignore")
            if not (path.name.startswith("2010") or re.search(r"2010年\d{1,2}月\d{1,2}日", raw[:1800])):
                continue
            title, _, official, body = clean_rst(raw)
            if not title or not official or RUAN_EXCLUDE.search(title):
                continue
            # Avoid translations and third-party extracts; retain the author's own commentary/essays.
            if RUAN_TRANSLATION.search(title) or "文章来源" in raw or "译者" in raw[:1600]:
                continue
            if root.name == "sci-tech" and not re.search(r"开源|封闭|互联网|音乐家|版权|出版|电子书|商业|文化|评论|观察|社会|用户|产品|未来|Android|Google|苹果|微软", title, re.I):
                continue
            if root.name == "misc" and not re.search(r"总结|回顾|写作|博客|生活|工作|阅读|思考", title):
                continue
            key = official.replace("http://", "https://")
            if key in seen:
                continue
            item = make_item(
                path, "阮一峰的网络日志", "阮一峰",
                "CC BY-NC-ND 3.0: verbatim main-body reproduction in a noncommercial collection; no textual rewriting",
                "https://www.ruanyifeng.com/blog/2008/04/creative_commons_licenses.html",
                "正文原句未改写；仅从页面/RST 中分离标题、作者/日期、链接标记、图注和文末说明。按非商业、署名、禁止演绎条件使用。",
                min_score=-3.0 if root.name in {"opinions", "essays"} else 0.0,
            )
            if item:
                seen.add(key)
                items.append(item)
    print("RUAN_DYNAMIC", len(items), sum(x["char_count"] for x in items), flush=True)
    return items


def gather_pongba_fixed():
    items = []
    root = SOURCE_REPO / "pongba" / "allpapers"
    if not root.exists():
        return items
    for path in sorted(root.glob("2010*.rst")):
        raw = path.read_text(encoding="utf-8", errors="ignore")
        title, _, official, body = clean_rst(raw)
        if not title or not official or count_chars(body) < 900:
            continue
        if re.search(r"转载|译文|翻译|译者|文章来源", title + raw[:1200]):
            continue
        item = make_item(
            path, "刘未鹏 | Mind Hacks", "刘未鹏",
            "Article-level repost permission: retain author, source and original hyperlink",
            official,
            "原文页明确要求转载时注明作者、出处与原始超链接；本包在 Excel/manifest 中完整保留这些信息。",
            min_score=-5.0,
        )
        if item:
            items.append(item)
    print("PONGBA_FIXED", len(items), sum(x["char_count"] for x in items), flush=True)
    return items


def main():
    if not SOURCE_REPO.exists():
        subprocess.run(["git", "clone", "--depth", "1", "https://github.com/me115/read.git", str(SOURCE_REPO)], check=True)
    candidates = gather_coolshell_broad() + gather_ruan_dynamic() + gather_pongba_fixed()
    candidates = dedupe_candidates(candidates)
    print("CANDIDATES_V3", len(candidates), sum(x["char_count"] for x in candidates), flush=True)
    selected = choose_balanced(candidates)
    write_outputs_v2(selected, candidates)


if __name__ == "__main__":
    main()
