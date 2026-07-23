#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

from corpus_2010_o_temp import (
    LOWER, OUT, SOURCE_REPO, TARGET, TXT_DIR, UPPER,
    choose_balanced, clean_rst, count_chars, dedupe_candidates,
    normalize_text, opinion_score, safe_slug, topic_of,
)


def item_from_rst(path: Path, source_site: str, copyright_status: str, license_url: str,
                  min_score: float = 1.0, fixed_author: str | None = None,
                  note: str = ""):
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if not re.search(r"2010年\d{1,2}月\d{1,2}日", raw[:1800]):
        return None
    title, author, official, body = clean_rst(raw)
    if fixed_author:
        author = fixed_author
    if not title or not official or count_chars(body) < 600:
        return None
    score = opinion_score(title, body, str(path))
    if score < min_score:
        return None
    return {
        "title": title,
        "author": author or fixed_author or "未标明",
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


COOLSHELL_EXCLUDE = re.compile(
    r"Windows编程革命简史|版本管理器的发展史|免费开源的数据挖掘软件|代码优化概要|"
    r"管理并设计你的口令|Jeff Dean|低速率网络|在Javascript里写Python|"
    r"下载|安装|语法|函数|源码|正则表达式|命令行|配置文件|性能测试|编译器教程|"
    r"数据库教程|HTML|CSS|jQuery|C\+\+|\.NET|JavaScript.*教程|Python.*教程",
    re.I,
)
COOLSHELL_INCLUDE = re.compile(
    r"程序员|架构师|团队|职场|工作|公司|管理|创业|文化|观点|思考|误区|建议|"
    r"经验|教训|失败|成功|设计的失误|应该避免|不要|为什么|未来|开源|黑客|"
    r"用户|产品|互联网|软件工程|编程观点|代码注释|命名|偷了世界"
)


def gather_coolshell_broad():
    items = []
    seen = set()
    for path in (SOURCE_REPO / "coolshell").rglob("*.rst"):
        raw = path.read_text(encoding="utf-8", errors="ignore")
        if "2010年" not in raw[:1800]:
            continue
        title, _, _, _ = clean_rst(raw)
        if not title or COOLSHELL_EXCLUDE.search(title):
            continue
        if not COOLSHELL_INCLUDE.search(title) and not re.search(r"career|story", str(path)):
            continue
        article_id = re.search(r"articles(\d+)", path.name)
        key = article_id.group(1) if article_id else str(path)
        if key in seen:
            continue
        item = item_from_rst(
            path, "CoolShell",
            "Official repost permission with attribution and original source",
            "https://coolshell.cn/about", min_score=1.0,
            note="正文来自公开文集镜像并关联 CoolShell 官方原文；移除页面元数据、图片/代码块及文末编辑说明。",
        )
        if item:
            seen.add(key)
            items.append(item)
    print("COOLSHELL", len(items), sum(x["char_count"] for x in items), flush=True)
    return items


RUAN_WHITELIST = [
    "ruanyifeng/opinions/201012_in_memory_of_renlan.rst",
    "ruanyifeng/opinions/201009_when_japan_collapses.rst",
    "ruanyifeng/opinions/201009_where_i_am_going.rst",
    "ruanyifeng/opinions/201008_it_book_publishing.rst",
    "ruanyifeng/opinions/201008_unaccomplished_revolution.rst",
    "ruanyifeng/opinions/201007_sky_blue_and_black.rst",
    "ruanyifeng/opinions/201007_what_the_blue_lion_publishing_house_is_like.rst",
    "ruanyifeng/opinions/201005_shanghai_acid_rain.rst",
    "ruanyifeng/opinions/201005_good_at_talking_good_at_doing.rst",
    "ruanyifeng/opinions/201005_an_unsinkable_tpb.rst",
    "ruanyifeng/opinions/201004_talk_with_wangjianshuo.rst",
    "ruanyifeng/opinions/201004_about_campus_folk.rst",
    "ruanyifeng/opinions/201001_google_to_quit_china.rst",
    "ruanyifeng/essays/201010_sovereignty.rst",
    "ruanyifeng/essays/201010_what_is_margin.rst",
    "ruanyifeng/essays/201008_how_did_nevada_develop_its_economy.rst",
    "ruanyifeng/essays/201007_interesting_economic_history.rst",
    "ruanyifeng/essays/201001_until_they_are_old_and_dead.rst",
    "ruanyifeng/essays/201001_why_we_should_tolerate_wrong_words.rst",
    "ruanyifeng/essays/201001_england_in_16th_century_vs_china_in_21st_century.rst",
]
RUAN_SCI_EXCLUDE = re.compile(r"教程|算法|编程|代码|函数|语法|安装|下载|API|Javascript|jQuery|CSS|HTML|正则|配置|源码", re.I)
RUAN_SCI_INCLUDE = re.compile(r"开源|封闭|音乐家|互联网|Google|苹果|微软|版权|出版|电子书|商业|未来|文化|评论|观察|为什么|社会|用户|产品")


def gather_ruan():
    items = []
    for rel in RUAN_WHITELIST:
        path = SOURCE_REPO / rel
        if not path.exists():
            print("MISSING_RUAN", rel, flush=True)
            continue
        item = item_from_rst(
            path, "阮一峰的网络日志",
            "CC BY-NC-ND 3.0: verbatim main-body reproduction in a noncommercial collection; no textual rewriting",
            "https://www.ruanyifeng.com/blog/2008/04/creative_commons_licenses.html",
            min_score=-2.0, fixed_author="阮一峰",
            note="正文句子未改写；仅分离标题、作者/日期、链接标记、图注及文末说明。按非商业、署名、禁止演绎条件使用。",
        )
        if item:
            items.append(item)
    sci_root = SOURCE_REPO / "ruanyifeng" / "sci-tech"
    if sci_root.exists():
        for path in sci_root.glob("2010*.rst"):
            raw = path.read_text(encoding="utf-8", errors="ignore")
            title, _, _, _ = clean_rst(raw)
            if not title or RUAN_SCI_EXCLUDE.search(title) or not RUAN_SCI_INCLUDE.search(title):
                continue
            if "译文" in title or "文章来源" in raw or "译者" in raw[:1200]:
                continue
            item = item_from_rst(
                path, "阮一峰的网络日志",
                "CC BY-NC-ND 3.0: verbatim main-body reproduction in a noncommercial collection; no textual rewriting",
                "https://www.ruanyifeng.com/blog/2008/04/creative_commons_licenses.html",
                min_score=0.5, fixed_author="阮一峰",
                note="正文句子未改写；仅分离页面元数据与 RST 标记。按非商业、署名、禁止演绎条件使用。",
            )
            if item:
                items.append(item)
    print("RUAN", len(items), sum(x["char_count"] for x in items), flush=True)
    return items


PONGBA_EXCLUDE = re.compile(r"转载|译文|翻译|书摘|推荐书目|招聘|通知")


def gather_pongba():
    items = []
    seen = set()
    root = SOURCE_REPO / "pongba"
    if not root.exists():
        return items
    for path in root.rglob("*.rst"):
        raw = path.read_text(encoding="utf-8", errors="ignore")
        if not re.search(r"2010年\d{1,2}月\d{1,2}日", raw[:1800]):
            continue
        title, _, official, body = clean_rst(raw)
        if not title or PONGBA_EXCLUDE.search(title) or "译者" in raw[:1500] or "文章来源" in raw:
            continue
        if count_chars(body) < 900:
            continue
        if opinion_score(title, body, str(path)) < 0.0 and not re.search(r"思维|学习|阅读|判断|时间|方法|生活|心理|认知|知识|问题|为什么|如何", title):
            continue
        key = official or hashlib.sha1(re.sub(r"\s+", "", body).encode()).hexdigest()
        if key in seen:
            continue
        item = item_from_rst(
            path, "刘未鹏 | Mind Hacks",
            "Article-level repost permission: retain author, source and original hyperlink",
            official or "https://mindhacks.cn/", min_score=-3.0, fixed_author="刘未鹏",
            note="原文页要求转载注明作者、出处及原始超链接；本包在 Excel/manifest 中保留完整署名与官方链接。",
        )
        if item:
            seen.add(key)
            items.append(item)
    print("PONGBA", len(items), sum(x["char_count"] for x in items), flush=True)
    return items


def write_outputs_v2(selected, all_candidates):
    if OUT.exists():
        shutil.rmtree(OUT)
    TXT_DIR.mkdir(parents=True, exist_ok=True)
    rows, merged = [], []
    total = 0
    for i, x in enumerate(selected, 1):
        text_id = f"2010_O_{i:03d}"
        filename = f"{text_id}_{safe_slug(x['title'])}_cleaned.txt"
        body = normalize_text(x["body"])
        chars = count_chars(body)
        (TXT_DIR / filename).write_text(body + "\n", encoding="utf-8")
        merged.append(body)
        total += chars
        row = {k: v for k, v in x.items() if k != "body"}
        row.update({"id": i, "text_id": text_id, "bin": "bin01", "first_publication_year": 2010,
                    "language": "simplified", "char_count": chars, "ocr_quality": "copiable", "filename": filename})
        rows.append(row)
    (OUT / "2010_O_all_cleaned.txt").write_text("\n\n".join(merged) + "\n", encoding="utf-8")
    payload = {"year": 2010, "target_chars": TARGET, "actual_chars": total,
               "count_method": "Unicode characters excluding whitespace", "article_count": len(rows),
               "sources": dict(Counter(x["source_site"] for x in selected)),
               "source_chars": {s: sum(x["char_count"] for x in selected if x["source_site"] == s) for s in sorted(set(x["source_site"] for x in selected))},
               "topics": dict(Counter(x["topic"] for x in selected)), "rows": rows}
    (OUT / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "candidate_audit.json").write_text(json.dumps([{k:v for k,v in x.items() if k != "body"} for x in all_candidates], ensure_ascii=False, indent=2), encoding="utf-8")
    audit_dir = OUT / "candidate_texts"
    audit_dir.mkdir(exist_ok=True)
    for j, x in enumerate(sorted(all_candidates, key=lambda z:(z['source_site'], z['title'])), 1):
        (audit_dir / f"{j:03d}_{safe_slug(x['source_site'])}_{safe_slug(x['title'])}.txt").write_text(x['body'] + "\n", encoding="utf-8")
    licence = f"""2010_O 版权与清洗说明

用途：非商业学术语料研究。
实际正文字符数：{total:,}（排除空格、制表符与换行）。
文章数量：{len(rows)}。

来源及授权：
1. CoolShell：官方说明允许转载，须保留作者和原始出处。https://coolshell.cn/about
2. 阮一峰的网络日志：自由转载—非商用—非衍生—保持署名。正文原句未改写，仅从网页/RST 中分离正文与页面元数据。https://www.ruanyifeng.com/blog/2008/04/creative_commons_licenses.html
3. 刘未鹏 | Mind Hacks：文章页明确要求转载时注明作者、出处和原始超链接；这些信息均保留在 Excel 与 manifest.json。

清洗：排除标题、作者/日期行、导航、标签、广告、图片及图注、代码块、评论区、相关推荐、参考资料/参考文献和文末编辑说明；删除方括号数字型引用标记。正文句子、段落顺序和标点尽量保持原样。

本包不得商用。任何再分发必须继续保留作者、官方链接和版权状态；阮一峰文本不得进行改写或演绎。
"""
    (OUT / "LICENSE_AND_CLEANING.txt").write_text(licence, encoding="utf-8")
    summary = {"actual_chars": total, "article_count": len(rows), "within_target_band": LOWER <= total <= UPPER,
               "sources": payload["sources"], "source_chars": payload["source_chars"]}
    (OUT / "build_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("FINAL", json.dumps(summary, ensure_ascii=False), flush=True)
    if not (LOWER <= total <= UPPER):
        raise SystemExit(f"Target validation failed: {total} not in [{LOWER}, {UPPER}]")


def main():
    if not SOURCE_REPO.exists():
        subprocess.run(["git", "clone", "--depth", "1", "https://github.com/me115/read.git", str(SOURCE_REPO)], check=True)
    candidates = gather_coolshell_broad() + gather_ruan() + gather_pongba()
    candidates = dedupe_candidates(candidates)
    print("CANDIDATES", len(candidates), sum(x["char_count"] for x in candidates), flush=True)
    selected = choose_balanced(candidates)
    write_outputs_v2(selected, candidates)


if __name__ == "__main__":
    main()
