#!/usr/bin/env python3
"""GitHub-snapshot-only 2013 Simplified Chinese O corpus builder."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup
from opencc import OpenCC

YEAR = 2013
TARGET = 110_000
LOW = 108_500
HIGH = 111_500
OUT = Path("build/2013_O")
CC = OpenCC("t2s")
BAD_DOMAINS = ("sciscanpub.com", "sciscan.org", "hanspub.org")

RUANYF_REPO = "https://github.com/me115/read.git"
RUANYF_COMMIT = "fefdaad7192612e56f9d0f8fa65938b364e1b82a"
COOLSHELL_REPO = "https://github.com/ghostincoolshell/haoel-articles.git"
COOLSHELL_COMMIT = "ba4cb2e19730d13ab92a1a0ced8c0798c6f32982"
GOV_REPO = "https://github.com/cedarliu0906/Final-Project-Cedar-and-Shuping.git"
GOV_COMMIT = "7438f4e053efc24cdc166f0591a58cfc2e54a1ec"
PUBLIC_LICENSE_URL = "https://www.ncac.gov.cn/xxfb/flfg/flfg_532/202103/t20210309_50530.html"

MARKERS = re.compile(r"\[(?:\d+|\d+[–—-]\d+)(?:\s*[,，;；]\s*\d+)*\]|[⁰¹²³⁴⁵⁶⁷⁸⁹]+")
FORBIDDEN = re.compile(r"参考文献|责任编辑[:：]|版权声明[:：]|文档信息|相关文章|留言（?\d*条")


def nows(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def cjk(text: str) -> int:
    return len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", text))


def clone_at(url: str, commit: str, dest: Path) -> None:
    shutil.rmtree(dest, ignore_errors=True)
    subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", url, str(dest)], check=True)
    subprocess.run(["git", "-C", str(dest), "checkout", commit], check=True)


def normalize_line(value: str) -> str:
    value = CC.convert(value).replace("\u200b", "").replace("\ufeff", "").replace("\xa0", " ")
    value = MARKERS.sub("", value)
    value = re.sub(r"https?://\S+", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def clean_paragraphs(values: list[str]) -> str:
    paragraphs: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = normalize_line(value)
        if not value:
            continue
        if value in seen and len(value) < 100:
            continue
        if re.fullmatch(r"(?:参考文献|参考资料|注释|脚注|外部链接|相关文章|留言|评论区|责任编辑|（完）|完)", value):
            break
        if re.match(r"^(?:作者|日期|发表日期|分类|标签|来源|责任编辑|上一篇|下一篇)[:：]", value):
            continue
        seen.add(value)
        paragraphs.append(value)
    return "\n\n".join(paragraphs).strip()


def slug(title: str) -> str:
    label = "text"
    for key, value in {
        "政府工作报告": "gov_report",
        "未来": "future",
        "比特币": "bitcoin",
        "版权": "copyright",
        "程序员": "programmer",
        "效率": "efficiency",
        "创业": "startup",
        "互联网": "internet",
        "教育": "education",
        "经济": "economy",
        "设计": "design",
    }.items():
        if key in title:
            label = value
            break
    return f"{label}_{hashlib.md5(title.encode()).hexdigest()[:8]}"


def add(pool: list[dict], *, title: str, author: str, date: str, source_url: str,
        official_url: str, platform: str, genre: str, rights: str,
        license_url: str, text: str, notes: str) -> None:
    text = text.strip()
    if nows(text) < 700 or cjk(text) < 500:
        return
    if cjk(text) / max(nows(text), 1) < 0.48:
        return
    if any(domain in source_url.lower() for domain in BAD_DOMAINS):
        return
    text_id = slug(title)
    existing = {row["text_id"] for row in pool}
    base = text_id
    index = 2
    while text_id in existing:
        text_id = f"{base}_{index}"
        index += 1
    body_hash = hashlib.sha256(re.sub(r"\s+", "", text).encode()).hexdigest()
    pool.append({
        "text_id": text_id,
        "title": CC.convert(title),
        "author": author,
        "source_date": date,
        "source_url": source_url,
        "official_url": official_url,
        "source_platform": platform,
        "genre": genre,
        "copyright_status": rights,
        "license_url": license_url,
        "text": text,
        "file_name": f"2013_O_{text_id}_cleaned.txt",
        "char_count": nows(text),
        "cjk_count": cjk(text),
        "paragraphs": len(text.split("\n\n")),
        "sha256": body_hash,
        "notes": notes,
    })


def rst_title(raw: str, fallback: str) -> str:
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        value = line.strip()
        if not value or value.startswith(".. _"):
            continue
        if i + 1 < len(lines) and re.fullmatch(r"[=\-~`^*+#]{3,}", lines[i + 1].strip()):
            return CC.convert(value)
        if len(value) > 4 and not value.startswith(".."):
            return CC.convert(value)
    return fallback


def clean_rst(raw: str) -> str:
    lines = raw.splitlines()
    title_skipped = False
    values: list[str] = []
    in_literal = False
    in_note = False
    for i, line in enumerate(lines):
        stripped = line.rstrip()
        value = stripped.strip()
        if not value:
            in_literal = False
            if not in_note:
                values.append("")
            continue
        if value.startswith(".. note::") or value.startswith(".. image::") or value.startswith(".. figure::"):
            in_note = True
            continue
        if in_note:
            if line.startswith(" ") or line.startswith("\t"):
                continue
            in_note = False
        if value.startswith(".. ") or value.startswith(":"):
            continue
        if re.fullmatch(r"[=\-~`^*+#]{3,}", value):
            continue
        if not title_skipped:
            title_skipped = True
            continue
        if value.endswith("::"):
            in_literal = True
            value = value[:-2].strip()
            if value:
                values.append(value)
            continue
        if in_literal and (line.startswith(" ") or line.startswith("\t")):
            continue
        if re.fullmatch(r"阮一峰\s*/\s*2013[-/].*", value):
            continue
        if value in {"（完）", "(完)", "完"}:
            break
        # Remove RST links while retaining visible labels.
        value = re.sub(r"`([^`<>]+?)\s*<[^>]+>`__?", r"\1", value)
        value = re.sub(r"`([^`]+)`__?", r"\1", value)
        value = value.replace("\\ ", "").replace("\\", "")
        # Omit quote blocks and list-only citations, but keep ordinary prose lists.
        if (line.startswith("    ") or line.startswith("\t")) and len(value) > 30:
            continue
        if re.match(r"^(?:原文地址|作者|编辑)[:：]", value):
            continue
        values.append(value)
    # Preserve paragraph boundaries and join hard-wrapped lines.
    paragraphs: list[str] = []
    current: list[str] = []
    for value in values:
        if value == "":
            if current:
                paragraphs.append("".join(current))
                current = []
        else:
            current.append(value)
    if current:
        paragraphs.append("".join(current))
    return clean_paragraphs(paragraphs)


def original_url(raw: str) -> str:
    match = re.search(r"https?://(?:www\.)?ruanyifeng\.com/blog/2013/\d{2}/[^\s>`]+\.html", raw)
    return match.group(0) if match else "https://www.ruanyifeng.com/blog/archives.html"


def collect_ruanyf(pool: list[dict], repo: Path) -> None:
    include_dirs = {"opinions", "essays", "clipboard", "sci-tech", "notes", "business", "books"}
    exclude_title = re.compile(r"教程|算法|安装|配置|JavaScript|jQuery|CORS|RSA|GPG|PostgreSQL|正则|命令|API|Linux启动")
    for path in sorted((repo / "ruanyifeng").rglob("2013*.rst")):
        if path.parent.name not in include_dirs:
            continue
        raw = path.read_text("utf-8", errors="ignore")
        title = rst_title(raw, path.stem)
        if exclude_title.search(title):
            continue
        body = clean_rst(raw)
        date_match = re.match(r"(2013)(\d{2})", path.name)
        date = f"2013-{date_match.group(2)}" if date_match else "2013"
        official = original_url(raw)
        source = (
            "https://github.com/me115/read/blob/"
            f"{RUANYF_COMMIT}/" + quote(str(path.relative_to(repo)), safe="/")
        )
        genre = "书评 / 影评 / 文化评论" if re.search(r"书|序言|读后感|纪录片|电影", title) else "观点 / 社会与科技评论"
        add(pool, title=title, author="阮一峰", date=date, source_url=source,
            official_url=official, platform="阮一峰文章固定仓库快照", genre=genre,
            rights="CC BY-NC-ND 3.0 (original site-level license)",
            license_url="https://creativecommons.org/licenses/by-nc-nd/3.0/",
            text=body,
            notes=f"Fixed GitHub mirror commit; official_url={official}; original site states 自由转载-非商用-非衍生-保持署名; RST metadata, links, quotations and back matter removed.")
    print("RUANYF", len([x for x in pool if x["source_platform"] == "阮一峰文章固定仓库快照"]))


def clean_markdown(raw: str) -> str:
    raw = re.split(r"转载本站文章请注明作者和出处|请勿用于任何商业用途|相关文章", raw)[0]
    raw = re.sub(r"```.*?```", "", raw, flags=re.S)
    soup = BeautifulSoup(__import__("markdown").markdown(raw, extensions=["extra"]), "lxml")
    for selector in "script style img figure figcaption table pre code blockquote".split():
        for node in soup.select(selector):
            node.decompose()
    return clean_paragraphs([e.get_text(" ", strip=True) for e in soup.find_all(["h2", "h3", "h4", "p", "li"])])


def collect_coolshell(pool: list[dict], repo: Path) -> None:
    exclude = re.compile(r"译文|翻译|摘录|教程|速查|Cheat|资源列表")
    for path in sorted((repo / "blogs/rss2html2markdown").glob("2013-*.md")):
        title = re.sub(r"^2013-\d{1,2}-\d{1,2}\s+", "", path.stem)
        if exclude.search(title):
            continue
        raw = path.read_text("utf-8", errors="ignore")
        body = clean_markdown(raw)
        date_match = re.match(r"(2013-\d{1,2}-\d{1,2})", path.stem)
        date = date_match.group(1) if date_match else "2013"
        official_match = re.search(r"https://coolshell\.cn/articles/\d+\.html", raw)
        official = official_match.group(0) if official_match else "https://coolshell.cn/"
        source = (
            "https://github.com/ghostincoolshell/haoel-articles/blob/"
            f"{COOLSHELL_COMMIT}/" + quote(str(path.relative_to(repo)), safe="/")
        )
        genre = "科技评论 / 技术复盘" if re.search(r"编程|软件|系统|技术|代码|语言|设计", title) else "职场 / 社会评论"
        add(pool, title=title, author="陈皓 / CoolShell", date=date,
            source_url=source, official_url=official,
            platform="CoolShell 固定仓库快照", genre=genre,
            rights="Author-permitted attribution; noncommercial only",
            license_url="https://coolshell.cn/", text=body,
            notes=f"Fixed repository commit; official_url={official}; article footer permits attribution/noncommercial redistribution; code, images, quotes and back matter removed.")
    print("COOLSHELL", len([x for x in pool if x["source_platform"] == "CoolShell 固定仓库快照"]))


def collect_government(pool: list[dict], repo: Path) -> None:
    path = repo / "data/Analyze/2013年中华人民共和国国务院政府工作报告.txt"
    raw = path.read_text("utf-8", errors="ignore")
    start = raw.find("各位代表")
    if start >= 0:
        raw = raw[start:]
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    body = clean_paragraphs(lines)
    source = (
        "https://github.com/cedarliu0906/Final-Project-Cedar-and-Shuping/blob/"
        f"{GOV_COMMIT}/data/Analyze/2013%E5%B9%B4%E4%B8%AD%E5%8D%8E%E4%BA%BA%E6%B0%91%E5%85%B1%E5%92%8C%E5%9B%BD%E5%9B%BD%E5%8A%A1%E9%99%A2%E6%94%BF%E5%BA%9C%E5%B7%A5%E4%BD%9C%E6%8A%A5%E5%91%8A.txt"
    )
    add(pool, title="2013年中华人民共和国国务院政府工作报告", author="中华人民共和国国务院",
        date="2013-03-05", source_url=source,
        official_url="https://www.gov.cn/2013lh/content_2356362.htm",
        platform="政府公开报告固定仓库快照", genre="政府工作回顾 / 政策评论",
        rights="Public domain: PRC Copyright Law Article 5 official document",
        license_url=PUBLIC_LICENSE_URL, text=body,
        notes="Official document; fixed text snapshot; title/source metadata removed; main report body only.")
    print("GOV", nows(body))


def excerpt(item: dict, needed: int) -> dict | None:
    paragraphs: list[str] = []
    total = 0
    for paragraph in item["text"].split("\n\n"):
        size = nows(paragraph)
        if paragraphs and total + size > needed + 350:
            break
        paragraphs.append(paragraph)
        total += size
        if total >= needed - 180:
            break
    if total < 700:
        return None
    result = item.copy()
    result["text"] = "\n\n".join(paragraphs)
    result["text_id"] += "_excerpt"
    result["title"] += "（正文节选）"
    result["file_name"] = f"2013_O_{result['text_id']}_cleaned.txt"
    result["char_count"] = nows(result["text"])
    result["cjk_count"] = cjk(result["text"])
    result["paragraphs"] = len(paragraphs)
    result["sha256"] = hashlib.sha256(re.sub(r"\s+", "", result["text"]).encode()).hexdigest()
    result["notes"] += " Paragraph-boundary excerpt used only to balance the bin; no rewriting, repetition or padding."
    return result


def choose_bins(pool: list[dict]) -> tuple[list[list[dict]], list[dict]]:
    unique: list[dict] = []
    hashes: set[str] = set()
    for item in pool:
        if item["sha256"] not in hashes:
            hashes.add(item["sha256"])
            unique.append(item)
    # Alternate by platform and size to ensure each bin contains at least two sources.
    source_groups = {name: sorted([x for x in unique if x["source_platform"] == name], key=lambda x: x["char_count"], reverse=True)
                     for name in sorted({x["source_platform"] for x in unique})}
    bins: list[list[dict]] = [[], []]
    totals = [0, 0]
    used: set[int] = set()
    for group in source_groups.values():
        for item in group[:2]:
            target_bin = 0 if totals[0] <= totals[1] else 1
            if totals[target_bin] + item["char_count"] <= TARGET + 250:
                bins[target_bin].append(item)
                totals[target_bin] += item["char_count"]
                used.add(id(item))
    remaining = sorted([x for x in unique if id(x) not in used], key=lambda x: x["char_count"], reverse=True)
    progress = True
    while progress:
        progress = False
        for index in sorted(range(2), key=lambda i: totals[i]):
            fits = [x for x in remaining if totals[index] + x["char_count"] <= TARGET + 250]
            if fits and totals[index] < TARGET - 500:
                item = fits[0]
                bins[index].append(item)
                totals[index] += item["char_count"]
                remaining.remove(item)
                used.add(id(item))
                progress = True
    for index in range(2):
        if totals[index] < LOW:
            needed = TARGET - totals[index]
            candidates = sorted([x for x in remaining if x["char_count"] >= needed - 450], key=lambda x: abs(x["char_count"] - needed))
            if candidates:
                part = excerpt(candidates[0], needed)
                if part:
                    bins[index].append(part)
                    totals[index] += part["char_count"]
                    remaining.remove(candidates[0])
                    used.add(id(candidates[0]))
    return bins, [x for x in unique if id(x) not in used]


def write_outputs(bins: list[list[dict]], unused: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for number, selected in enumerate(bins, 1):
        bin_name = f"2013_O_bin{number:02d}"
        for item in selected:
            item["bin"] = bin_name
            (OUT / item["file_name"]).write_text(item["text"] + "\n", encoding="utf-8")
            row = {k: v for k, v in item.items() if k != "text"}
            row["index"] = len(rows) + 1
            rows.append(row)
        (OUT / f"{bin_name}_cleaned.txt").write_text("\n\n".join(x["text"] for x in selected) + "\n", encoding="utf-8")
    fields = ["index", "text_id", "bin", "source_date", "title", "author", "source_platform", "genre", "source_url", "official_url", "copyright_status", "license_url", "file_name", "char_count", "cjk_count", "paragraphs", "sha256", "notes"]
    with (OUT / "manifest.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)
    (OUT / "manifest.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    with (OUT / "excluded_candidates.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["title", "source_platform", "source_url", "reason"])
        for item in unused:
            writer.writerow([item["title"], item["source_platform"], item["source_url"], "licensed/open candidate not selected after balancing"])
        writer.writerow(["SCISCAN / 汉斯出版社", "excluded", "", "explicitly excluded by user"])
        writer.writerow(["知乎 / 豆瓣未授权全文", "excluded", "", "public readability is not redistribution permission"])
    issues: list[str] = []
    stats: list[dict] = []
    for number, selected in enumerate(bins, 1):
        bin_name = f"2013_O_bin{number:02d}"
        text = (OUT / f"{bin_name}_cleaned.txt").read_text("utf-8")
        stat = {"bin": bin_name, "non_whitespace_chars": nows(text), "cjk_chars": cjk(text), "files": len(selected), "platforms": sorted({x["source_platform"] for x in selected})}
        stats.append(stat)
        if not LOW <= stat["non_whitespace_chars"] <= HIGH:
            issues.append(f"{bin_name} count outside range: {stat['non_whitespace_chars']}")
        if len(stat["platforms"]) < 2:
            issues.append(f"{bin_name} lacks source diversity")
    if len({row["sha256"] for row in rows}) != len(rows):
        issues.append("duplicate source text hash detected")
    for row in rows:
        text = (OUT / row["file_name"]).read_text("utf-8")
        if FORBIDDEN.search(text) or MARKERS.search(text):
            issues.append(row["text_id"] + " contains non-body marker")
        if not row["source_date"].startswith("2013"):
            issues.append(row["text_id"] + " wrong year")
        if any(domain in row["source_url"].lower() for domain in BAD_DOMAINS):
            issues.append(row["text_id"] + " forbidden source")
    qa = {"status": "PASS" if not issues else "FAIL", "year": YEAR, "target_per_bin": TARGET, "accepted_range": [LOW, HIGH], "bins": stats, "selected_documents": len(rows), "source_platforms": sorted({row["source_platform"] for row in rows}), "excluded_publishers": ["SCISCAN", "Hans Publishers / 汉斯出版社"], "issues": issues}
    (OUT / "qa_report.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    report = ["# 2013_O Quality Assurance Report", "", f"**Status: {qa['status']}**", ""]
    for stat in stats:
        report += [f"## {stat['bin']}", f"- Non-whitespace characters: {stat['non_whitespace_chars']:,}", f"- CJK characters: {stat['cjk_chars']:,}", f"- Individual source files: {stat['files']}", f"- Source platforms: {', '.join(stat['platforms'])}", ""]
    report += ["## Compliance", "- Main text only; title/byline/date, images, tables, captions, code, quotations, references and back matter removed.", "- No fabricated text, duplicated padding or paraphrasing.", "- SCISCAN, Hans Publishers, and unlicensed Zhihu/Douban full text excluded.", "", "## Issues"]
    report += [f"- {issue}" for issue in issues] if issues else ["- None detected."]
    (OUT / "QA_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(f"# 2013_O Corpus\n\nTwo Simplified Chinese Opinion/Commentary/Review bins. Bin01: {stats[0]['non_whitespace_chars']:,}; Bin02: {stats[1]['non_whitespace_chars']:,} non-whitespace characters.\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    if issues:
        raise SystemExit("QA failed")


def main() -> None:
    shutil.rmtree(OUT, ignore_errors=True)
    root = Path("/tmp/corpus2013_sources")
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    ruanyf = root / "read"
    coolshell = root / "haoel"
    gov = root / "gov"
    clone_at(RUANYF_REPO, RUANYF_COMMIT, ruanyf)
    clone_at(COOLSHELL_REPO, COOLSHELL_COMMIT, coolshell)
    clone_at(GOV_REPO, GOV_COMMIT, gov)
    pool: list[dict] = []
    collect_ruanyf(pool, ruanyf)
    collect_coolshell(pool, coolshell)
    collect_government(pool, gov)
    total = sum(x["char_count"] for x in pool)
    print("POOL", len(pool), total, sorted({x["source_platform"] for x in pool}))
    if total < 225_000:
        raise SystemExit(f"insufficient pool: {total}")
    bins, unused = choose_bins(pool)
    print("BIN_RAW", [sum(x["char_count"] for x in selected) for selected in bins])
    write_outputs(bins, unused)


if __name__ == "__main__":
    main()
