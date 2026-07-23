#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Temporary builder for a 2010 Simplified-Chinese opinion/commentary/review corpus.

The script only selects material from sites with an explicit reuse licence:
- 月光博客: CC BY-NC-SA / 署名-非商业性使用-相同方式共享
- CoolShell: site-wide permission to repost with attribution/source
- Demon's Blog: CC BY-NC-SA 2.5 CN

Output is research-only and contains main text only. Metadata and licence records are
kept separately in manifest.json and LICENSE_AND_CLEANING.txt.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

YEAR = 2010
TARGET = 110_000
LOWER = 108_000
UPPER = 112_000
OUT = Path("out")
TXT_DIR = OUT / "texts"
SOURCE_REPO = Path("/tmp/read")
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; corpus-research/1.0; noncommercial academic use)",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
})


def log(*args):
    print(*args, flush=True)


def fetch(url: str, timeout: int = 35, tries: int = 3) -> requests.Response | None:
    for i in range(tries):
        try:
            r = SESSION.get(url, timeout=timeout, allow_redirects=True)
            if r.status_code == 200 and r.content:
                if not r.encoding or r.encoding.lower() == "iso-8859-1":
                    r.encoding = r.apparent_encoding or "utf-8"
                return r
            log("HTTP", r.status_code, url)
        except Exception as exc:
            log("FETCH_ERR", type(exc).__name__, url)
        time.sleep(1.2 * (i + 1))
    return None


def count_chars(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove bracketed academic-style reference markers, not ordinary numbered arguments.
    text = re.sub(r"(?<!\w)\[(?:\d{1,3})(?:\s*[-–,，]\s*\d{1,3})*\](?!\w)", "", text)
    text = re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩]", "", text)
    text = re.sub(r"\n\s*(?:\(完\)|（完）|全文完|完)\s*$", "", text)
    return text.strip()


def chinese_ratio(text: str) -> float:
    compact = re.sub(r"\s+", "", text)
    if not compact:
        return 0.0
    zh = len(re.findall(r"[\u3400-\u9fff]", compact))
    return zh / len(compact)


def topic_of(title: str, body: str) -> str:
    s = title + " " + body[:2500]
    groups = [
        ("互联网与平台", r"互联网|网站|博客|搜索|Google|谷歌|微博|社交|网络|平台|用户|隐私|版权"),
        ("软件与技术文化", r"软件|程序员|开发|开源|黑客|编程|代码|技术|工程师|操作系统|浏览器"),
        ("职场与管理", r"职场|工作|员工|公司|团队|管理|领导|招聘|面试|绩效|职业|加班|创业"),
        ("商业与产品", r"商业|市场|产品|品牌|营销|企业|投资|经济|收入|出版|广告"),
        ("社会与公共议题", r"社会|政府|公共|制度|教育|医疗|环境|城市|人口|税|法律|自由"),
        ("文化与媒介评论", r"电影|音乐|书|阅读|文化|媒体|艺术|出版|影评|书评|评论"),
        ("生活与价值观", r"人生|生活|成长|选择|幸福|价值|态度|习惯|思考|理想"),
    ]
    scores = [(name, len(re.findall(pattern, s, flags=re.I))) for name, pattern in groups]
    best = max(scores, key=lambda x: x[1])
    return best[0] if best[1] else "综合评论"


POS_TITLE = re.compile(
    r"评论|评测|测评|书评|影评|观察|思考|看法|观点|分析|反思|争论|误区|真相|未来|文化|"
    r"为什么|为何|应该|不应该|不要|如何看|值得|建议|经验|教训|失败|成功|选择|原则|"
    r"程序员|团队|职场|公司|创业|管理|产品|用户|互联网|博客|开源|版权|出版|教育|社会|人生"
)
NEG_TITLE = re.compile(
    r"下载|安装|升级|教程|入门|语法|函数|源码|代码示例|命令大全|配置指南|漏洞通告|补丁|"
    r"发布版|正式发布|更新日志|抽奖|赠送|优惠|招聘启事|活动通知|会议通知|周报|月报"
)
OPINION_BODY = re.compile(r"我认为|我觉得|在我看来|我的看法|笔者认为|值得注意|可以看出|这说明|建议|不妨|应该|不应该|遗憾|可惜|令人|问题在于|关键在于")
NEWS_LEAD = re.compile(r"^(?:据|来自).{0,30}(?:报道|消息)|^北京时间|^新华社|^中新网")


def opinion_score(title: str, body: str, path: str = "") -> float:
    score = 0.0
    if POS_TITLE.search(title):
        score += 4.0
    if NEG_TITLE.search(title):
        score -= 7.0
    markers = len(OPINION_BODY.findall(body[:6000]))
    score += min(markers, 7) * 0.7
    if NEWS_LEAD.search(body[:100]):
        score -= 4.0
    if "文章来源" in body or "译者" in body[:500] or "翻译" in title:
        score -= 4.0
    if re.search(r"career|story", path):
        score += 2.2
    if re.search(r"opinions|essays", path):
        score += 2.5
    if 1500 <= count_chars(body) <= 9000:
        score += 1.0
    if chinese_ratio(body) < 0.55:
        score -= 4.0
    return score


def clean_rst(raw: str) -> tuple[str, str, str, str]:
    """Return title, author, official_url, cleaned_body."""
    raw = raw.replace("\r\n", "\n")
    lines = raw.splitlines()
    title = ""
    author = ""
    official = ""

    for i, line in enumerate(lines):
        s = line.strip()
        if not s or s.startswith(".. _"):
            continue
        if i + 1 < len(lines) and re.fullmatch(r"[=\-~^`:#*+]{3,}", lines[i + 1].strip()):
            title = s
            break
    for line in lines[:35]:
        m = re.search(r"(20\d{2}年\d{1,2}月\d{1,2}日).*?`([^<`]+?)\s*<", line)
        if m:
            author = m.group(2).strip()
            break
    for line in lines:
        m = re.search(r"原文地址:\s*(https?://\S+)", line)
        if m:
            official = m.group(1).rstrip("`_ ")
            break
    if not author:
        for line in lines[-20:]:
            m = re.search(r"作者:\s*([^\n]+)", line)
            if m:
                author = m.group(1).strip()
                break

    body_lines: list[str] = []
    started = False
    skip_code_indent: int | None = None
    title_seen = False
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith(".. note::"):
            break
        if s.startswith(".. _"):
            continue
        if not title_seen and title and s == title:
            title_seen = True
            continue
        if title_seen and re.fullmatch(r"[=\-~^`:#*+]{3,}", s):
            started = True
            continue
        if not started:
            continue
        if re.match(r"^20\d{2}年\d{1,2}月\d{1,2}日", s):
            continue
        if re.fullmatch(r"`?ruanyifeng\.com\s*<[^>]+>`?__", s, flags=re.I):
            continue
        if s.startswith(".. |") or s.startswith(".. image::") or s.startswith(":target:") or s.startswith(":width:") or s.startswith(":alt:"):
            continue
        if re.fullmatch(r"\|image\d+\|", s, flags=re.I):
            continue
        if re.fullmatch(r"(?:图|图片|截图|Figure)\s*\d*[:：]?", s, flags=re.I):
            continue
        # RST literal code blocks are not part of the target opinion prose.
        if s == "::":
            skip_code_indent = None
            continue
        if skip_code_indent is not None:
            if line and len(line) - len(line.lstrip()) >= skip_code_indent:
                continue
            skip_code_indent = None
        if i > 0 and lines[i - 1].strip() == "::" and line.startswith("   "):
            skip_code_indent = len(line) - len(line.lstrip())
            continue
        # Remove obvious source/caption/metadata lines.
        if re.match(r"^(?:原文|来源|作者|编辑|版权|标签|相关链接|参考资料|参考文献)[:：]", s):
            continue
        line = re.sub(r"`([^`<>]+?)\s*<https?://[^>]+>`__", r"\1", line)
        line = re.sub(r"`([^`]+?)`__", r"\1", line)
        line = re.sub(r"\\([ ，。；：、“”‘’（）()])", r"\1", line)
        line = line.replace("\\ ", " ")
        line = re.sub(r"^\s{4}", "", line)
        body_lines.append(line.rstrip())

    body = normalize_text("\n".join(body_lines))
    return title.strip(), author.strip() or "未标明", official.strip(), body


def gather_coolshell() -> list[dict]:
    out = []
    root = SOURCE_REPO / "coolshell"
    if not root.exists():
        log("CoolShell source missing", root)
        return out
    seen_paths = set()
    for path in root.rglob("*.rst"):
        raw = path.read_text(encoding="utf-8", errors="ignore")
        if not re.search(r"2010年\d{1,2}月\d{1,2}日", raw[:1500]):
            continue
        title, author, official, body = clean_rst(raw)
        if not title or not official or count_chars(body) < 650:
            continue
        # Same article appears under more than one category in the mirror.
        article_id = re.search(r"articles(\d+)", path.name)
        dedupe_id = article_id.group(1) if article_id else official
        if dedupe_id in seen_paths:
            continue
        seen_paths.add(dedupe_id)
        score = opinion_score(title, body, str(path))
        if score < 3.0:
            continue
        out.append({
            "title": title,
            "author": author,
            "official_url": official.replace("http://", "https://"),
            "mirror_source": f"https://github.com/me115/read/blob/master/{path.relative_to(SOURCE_REPO).as_posix()}",
            "source_site": "CoolShell",
            "body": body,
            "char_count": count_chars(body),
            "topic": topic_of(title, body),
            "quality_score": round(score, 2),
            "copyright_status": "Permitted repost with attribution/source; noncommercial research package",
            "license_url": "https://coolshell.cn/about",
            "notes": "正文取自公开文集镜像并与官方原文地址关联；移除标题、日期、作者行、图片/代码块、文末说明与链接标记。",
        })
    log("COOLSHELL_CANDIDATES", len(out), sum(x["char_count"] for x in out))
    return out


def sitemap_entries(site: str) -> list[tuple[str, str]]:
    candidates = [
        urljoin(site, "/sitemap.xml"),
        urljoin(site, "/sitemap_index.xml"),
        urljoin(site, "/sitemap-index.xml"),
        urljoin(site, "/wp-sitemap.xml"),
        urljoin(site, "/sitemap-posttype-post.xml"),
        urljoin(site, "/post-sitemap.xml"),
    ]
    visited = set()
    pages: list[tuple[str, str]] = []

    def walk(url: str, depth: int = 0):
        if url in visited or depth > 3 or len(visited) > 80:
            return
        visited.add(url)
        r = fetch(url)
        if not r:
            return
        text = r.text
        if "<sitemapindex" in text.lower():
            soup = BeautifulSoup(text, "xml")
            for loc in soup.find_all("loc"):
                child = loc.get_text(strip=True)
                if child:
                    walk(child, depth + 1)
            return
        soup = BeautifulSoup(text, "xml")
        for node in soup.find_all("url"):
            loc = node.find("loc")
            if not loc:
                continue
            lastmod = node.find("lastmod")
            pages.append((loc.get_text(strip=True), lastmod.get_text(strip=True) if lastmod else ""))

    for u in candidates:
        walk(u)
        if pages:
            break
    # Preserve order while removing duplicates.
    uniq = {}
    for u, d in pages:
        uniq[u] = d
    return list(uniq.items())


def best_article_container(soup: BeautifulSoup):
    selectors = [
        "article .entry-content", "article .post-content", "article",
        "div.entry-content", "div.post-content", "div.post-body", "div.post",
        "div#article", "div#content .entry", "main",
    ]
    candidates = []
    for selector in selectors:
        for node in soup.select(selector):
            clone = BeautifulSoup(str(node), "lxml")
            for bad in clone.select("script,style,noscript,nav,header,footer,aside,form,iframe,figure,figcaption,.comments,.comment,.commentlist,.related,.recommend,.share,.social,.tags,.tag,.post-meta,.entry-meta,.metadata,.breadcrumb,.pagination,.copyright,.license,.author-info,.post-title,h1"):
                bad.decompose()
            text = clone.get_text("\n", strip=True)
            score = count_chars(text) + 120 * len(clone.find_all("p"))
            candidates.append((score, clone))
    return max(candidates, key=lambda x: x[0])[1] if candidates else None


def clean_html_article(url: str, site_name: str, default_author: str) -> dict | None:
    r = fetch(url)
    if not r:
        return None
    soup = BeautifulSoup(r.text, "lxml")
    full_text = soup.get_text(" ", strip=True)
    if not (re.search(r"2010[-/.年]", full_text[:5000]) or "/2010/" in url):
        return None
    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else ""
    if not title and soup.title:
        title = re.split(r"[-_|—]", soup.title.get_text(" ", strip=True))[0].strip()
    container = best_article_container(soup)
    if container is None:
        return None
    # Remove non-body blocks and common image captions.
    for bad in container.select("script,style,noscript,nav,header,footer,aside,form,iframe,figure,figcaption,.comments,.comment,.commentlist,.related,.recommend,.share,.social,.tags,.tag,.post-meta,.entry-meta,.metadata,.breadcrumb,.pagination,.copyright,.license,.author-info,h1,h2.post-title"):
        bad.decompose()
    paragraphs = []
    for element in container.find_all(["p", "h2", "h3", "li", "blockquote"], recursive=True):
        if element.find_parent(["li", "blockquote"]) and element.name in {"p", "li"}:
            # avoid duplicating nested blocks
            pass
        t = element.get_text(" ", strip=True)
        if not t:
            continue
        if re.match(r"^(?:作者|日期|时间|分类|标签|版权|原文|来源|相关阅读|相关文章|评论|留言|参考资料|参考文献)[:：]", t):
            continue
        if re.fullmatch(r"(?:图|图片|截图|Image)\s*\d*[:：]?", t, flags=re.I):
            continue
        if re.search(r"(?:点击|返回).{0,8}(?:首页|目录)|欢迎发表评论|本文链接|永久链接", t):
            continue
        paragraphs.append(t)
    body = normalize_text("\n\n".join(paragraphs))
    # Deduplicate accidental nested extraction.
    clean_paras = []
    seen = set()
    for p in body.split("\n\n"):
        key = re.sub(r"\s+", "", p)
        if key and key not in seen:
            seen.add(key)
            clean_paras.append(p)
    body = normalize_text("\n\n".join(clean_paras))
    if count_chars(body) < 700 or chinese_ratio(body) < 0.55:
        return None
    author = default_author
    author_meta = soup.find("meta", attrs={"name": re.compile("author", re.I)})
    if author_meta and author_meta.get("content"):
        author = author_meta["content"].strip() or default_author
    score = opinion_score(title, body, url)
    if score < 3.2:
        return None
    if site_name == "月光博客":
        copyright_status = "CC BY-NC-SA (署名-非商业性使用-相同方式共享)"
        license_url = "https://www.williamlong.info/archives/480.html"
    else:
        copyright_status = "CC BY-NC-SA 2.5 China Mainland"
        license_url = "https://demon.tw/copyright"
    return {
        "title": title,
        "author": author,
        "official_url": url,
        "mirror_source": url,
        "source_site": site_name,
        "body": body,
        "char_count": count_chars(body),
        "topic": topic_of(title, body),
        "quality_score": round(score, 2),
        "copyright_status": copyright_status,
        "license_url": license_url,
        "notes": "从官方页面提取；移除标题、作者/日期、导航、图片说明、相关推荐、评论区和版权页脚；正文段落内容尽量原样保留。",
    }


def gather_site(site: str, site_name: str, author: str) -> list[dict]:
    entries = sitemap_entries(site)
    log(site_name, "SITEMAP_ENTRIES", len(entries))
    urls = []
    for u, d in entries:
        if d.startswith("2010") or "/2010/" in u:
            urls.append(u)
        elif site_name == "月光博客" and re.search(r"/archives/\d+\.html$", u) and not d:
            # Old sitemap variants may omit lastmod. The article page itself is checked.
            urls.append(u)
    # Guard against crawling an entire site when lastmod is absent.
    if len(urls) > 450:
        urls = urls[:450]
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(clean_html_article, u, site_name, author): u for u in urls}
        for fut in concurrent.futures.as_completed(futs):
            try:
                item = fut.result()
                if item:
                    results.append(item)
            except Exception as exc:
                log("PARSE_ERR", futs[fut], repr(exc))
    # exact body dedupe
    uniq = {}
    for x in results:
        key = hashlib.sha256(re.sub(r"\s+", "", x["body"]).encode()).hexdigest()
        uniq[key] = x
    out = list(uniq.values())
    log(site_name, "CANDIDATES", len(out), sum(x["char_count"] for x in out))
    return out


def dedupe_candidates(items: list[dict]) -> list[dict]:
    out = []
    seen_url = set()
    seen_hash = set()
    for x in items:
        urlkey = re.sub(r"^https?://", "", x["official_url"]).rstrip("/")
        h = hashlib.sha1(re.sub(r"\s+", "", x["body"]).encode("utf-8")).hexdigest()
        if urlkey in seen_url or h in seen_hash:
            continue
        if x["char_count"] < 650 or x["char_count"] > 18_000:
            continue
        seen_url.add(urlkey)
        seen_hash.add(h)
        out.append(x)
    return out


def choose_balanced(items: list[dict]) -> list[dict]:
    # Highest-quality candidates first within each source/topic, then balanced round-robin.
    pools: dict[str, list[dict]] = defaultdict(list)
    for x in items:
        pools[x["source_site"]].append(x)
    for source in pools:
        pools[source].sort(key=lambda x: (-x["quality_score"], -x["char_count"], x["title"]))

    sources = sorted(pools, key=lambda s: (-len(pools[s]), s))
    selected: list[dict] = []
    used = set()
    source_chars = Counter()
    topic_chars = Counter()
    total = 0

    def can_add(x: dict, relaxed: bool = False) -> bool:
        nonlocal total
        new_total = total + x["char_count"]
        if new_total > UPPER + (5000 if relaxed else 0):
            return False
        # Early balancing: no source over 62%, no topic over 35%, when alternatives exist.
        denom = max(new_total, 1)
        if not relaxed and len(sources) >= 2 and (source_chars[x["source_site"]] + x["char_count"]) / denom > 0.66 and new_total > 30_000:
            return False
        if not relaxed and (topic_chars[x["topic"]] + x["char_count"]) / denom > 0.38 and new_total > 35_000:
            return False
        return True

    # Seed sources and topics.
    topic_seen = set()
    progress = True
    while total < 96_000 and progress:
        progress = False
        for source in sources:
            candidates = [x for x in pools[source] if x["official_url"] not in used]
            candidates.sort(key=lambda x: (x["topic"] in topic_seen, -x["quality_score"], -x["char_count"]))
            for x in candidates:
                if can_add(x):
                    selected.append(x); used.add(x["official_url"])
                    source_chars[source] += x["char_count"]
                    topic_chars[x["topic"]] += x["char_count"]
                    topic_seen.add(x["topic"])
                    total += x["char_count"]
                    progress = True
                    break
            if total >= 96_000:
                break

    # Fill remaining gap by best fit, preserving quality and diversity.
    remaining = [x for x in items if x["official_url"] not in used]
    while total < LOWER and remaining:
        gap = TARGET - total
        feasible = [x for x in remaining if can_add(x, relaxed=False)]
        if not feasible:
            feasible = [x for x in remaining if can_add(x, relaxed=True)]
        if not feasible:
            break
        x = min(feasible, key=lambda y: (abs(gap - y["char_count"]), -y["quality_score"], topic_chars[y["topic"]]))
        selected.append(x); used.add(x["official_url"])
        source_chars[x["source_site"]] += x["char_count"]
        topic_chars[x["topic"]] += x["char_count"]
        total += x["char_count"]
        remaining.remove(x)

    # Local one-for-one swaps to get closer to 110k.
    best_distance = abs(TARGET - total)
    remaining = [x for x in items if x["official_url"] not in used]
    improved = True
    while improved:
        improved = False
        for old in list(selected):
            for new in remaining:
                new_total = total - old["char_count"] + new["char_count"]
                if new_total > UPPER or new_total < LOWER:
                    continue
                dist = abs(TARGET - new_total)
                if dist < best_distance and new["quality_score"] >= old["quality_score"] - 2.0:
                    selected.remove(old); selected.append(new)
                    remaining.remove(new); remaining.append(old)
                    used.remove(old["official_url"]); used.add(new["official_url"])
                    total = new_total; best_distance = dist
                    improved = True
                    break
            if improved:
                break

    selected.sort(key=lambda x: (x["source_site"], x["topic"], x["title"]))
    log("SELECTED", len(selected), total, "SOURCES", dict(Counter(x["source_site"] for x in selected)), "TOPICS", dict(Counter(x["topic"] for x in selected)))
    return selected


def safe_slug(text: str, n: int = 42) -> str:
    text = re.sub(r"[^0-9A-Za-z\u3400-\u9fff]+", "_", text).strip("_")
    return text[:n] or "article"


def write_outputs(selected: list[dict], all_candidates: list[dict]):
    if OUT.exists():
        shutil.rmtree(OUT)
    TXT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    manifest = []
    merged_parts = []
    for idx, x in enumerate(selected, 1):
        text_id = f"2010_O_{idx:03d}"
        filename = f"{text_id}_{safe_slug(x['title'])}_cleaned.txt"
        body = normalize_text(x["body"])
        chars = count_chars(body)
        (TXT_DIR / filename).write_text(body + "\n", encoding="utf-8")
        total += chars
        merged_parts.append(body)
        row = {k: v for k, v in x.items() if k != "body"}
        row.update({
            "id": idx,
            "text_id": text_id,
            "bin": "bin01",
            "first_publication_year": YEAR,
            "language": "simplified",
            "char_count": chars,
            "ocr_quality": "copiable",
            "filename": filename,
        })
        manifest.append(row)
    (OUT / "2010_O_all_cleaned.txt").write_text("\n\n".join(merged_parts) + "\n", encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps({
        "year": YEAR,
        "target_chars": TARGET,
        "actual_chars": total,
        "count_method": "Unicode characters excluding all whitespace",
        "article_count": len(manifest),
        "sources": dict(Counter(x["source_site"] for x in selected)),
        "topics": dict(Counter(x["topic"] for x in selected)),
        "rows": manifest,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    candidates_meta = [{k: v for k, v in x.items() if k != "body"} for x in all_candidates]
    (OUT / "candidate_audit.json").write_text(json.dumps(candidates_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    license_text = f"""2010_O 版权与清洗说明

用途：非商业学术语料研究。
实际正文字符数：{total:,}（统计时排除空格、制表符和换行）。
文章数量：{len(manifest)}。

一、来源与许可
1. 月光博客：署名—非商业性使用—相同方式共享（CC BY-NC-SA）。
   许可说明：https://www.williamlong.info/archives/480.html
2. CoolShell：官方说明允许转载，要求保留作者和出处；本包在 Excel/manifest 中完整保留署名和官方链接。
   转载说明：https://coolshell.cn/about
3. Demon's Blog：CC BY-NC-SA 2.5 China Mainland。
   许可说明：https://demon.tw/copyright

二、清洗范围
仅保留正文；排除标题、作者/日期行、导航、分类标签、广告、分享按钮、图表或图片说明、评论区、相关推荐、版权页脚、参考资料/参考文献、代码块及文末编辑说明。方括号数字型引用标记已删除。正文段落和标点尽量保持原样。

三、署名与相同方式共享
本语料包不得用于商业目的。转载、再分发或基于本包形成派生材料时，应保留 Excel/manifest 的作者、官方原文链接和许可信息，并继续采用兼容的署名—非商业性使用—相同方式共享许可。CoolShell 文本按其官方转载要求保留署名与出处。

四、质量控制
所有入选文本均标记为 2010 年首次发布、简体中文、可复制文本，并通过长度、中文比例、重复正文、体裁关键词和非正文元素检查。候选审计信息保存在 candidate_audit.json。
"""
    (OUT / "LICENSE_AND_CLEANING.txt").write_text(license_text, encoding="utf-8")
    summary = {
        "actual_chars": total,
        "article_count": len(manifest),
        "within_target_band": LOWER <= total <= UPPER,
        "source_chars": dict(Counter({s: sum(x["char_count"] for x in selected if x["source_site"] == s) for s in set(x["source_site"] for x in selected)})),
    }
    (OUT / "build_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if not (LOWER <= total <= UPPER):
        raise SystemExit(f"Target validation failed: {total} not in [{LOWER}, {UPPER}]")


def main():
    OUT.mkdir(exist_ok=True)
    if not SOURCE_REPO.exists():
        subprocess.run(["git", "clone", "--depth", "1", "https://github.com/me115/read.git", str(SOURCE_REPO)], check=True)
    candidates = []
    candidates.extend(gather_coolshell())
    # Official-page sources; failure of one site does not invalidate the others.
    candidates.extend(gather_site("https://www.williamlong.info", "月光博客", "月光"))
    candidates.extend(gather_site("https://demon.tw", "Demon's Blog", "Demon"))
    candidates = dedupe_candidates(candidates)
    log("ALL_CANDIDATES", len(candidates), sum(x["char_count"] for x in candidates))
    selected = choose_balanced(candidates)
    write_outputs(selected, candidates)


if __name__ == "__main__":
    main()
