#!/usr/bin/env python3
"""Build two ~110k-char Simplified Chinese O-type bins for 2013."""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import quote, urljoin

import markdown
import requests
from bs4 import BeautifulSoup
from opencc import OpenCC

YEAR = 2013
TARGET = 110_000
LOW = 108_500
HIGH = 111_500
OUT = Path("build/2013_O")
CC = OpenCC("t2s")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Academic corpus collection/2013-O (contact via GitHub)"})
LAST_WIKI = 0.0
BAD_DOMAINS = ("sciscanpub.com", "sciscan.org", "hanspub.org")

STOP = re.compile(r"^(参考文献|参考资料|注释|脚注|外部链接|参见|版本信息|文档信息|相关文章|留言|评论区|责任编辑)$")
META = re.compile(r"^(作者[:：]|日期[:：]|发表日期[:：]|版权声明[:：]|分类[:：]|标签[:：]|来源[:：]|责任编辑[:：]|上一篇[:：]|下一篇[:：]|目录$|全文完|（完）$)")
MARKERS = re.compile(r"\[(?:\d+|\d+[–—-]\d+)(?:\s*[,，;；]\s*\d+)*\]|[⁰¹²³⁴⁵⁶⁷⁸⁹]+")


def non_ws(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def cjk(text: str) -> int:
    return len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", text))


def fetch(url: str, params: dict | None = None, wiki: bool = False) -> requests.Response:
    global LAST_WIKI
    error: Exception | None = None
    for attempt in range(8):
        try:
            if wiki:
                delay = 1.35 - (time.monotonic() - LAST_WIKI)
                if delay > 0:
                    time.sleep(delay)
            response = SESSION.get(url, params=params, timeout=50)
            if wiki:
                LAST_WIKI = time.monotonic()
            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", "0") or 0)
                time.sleep(max(wait, 8 + attempt * 6))
                continue
            response.raise_for_status()
            return response
        except Exception as exc:
            error = exc
            time.sleep(min(20, 2 + attempt * 3))
    raise RuntimeError(f"{url}: {error}")


def clean_lines(lines: list[str]) -> str:
    result: list[str] = []
    seen: set[str] = set()
    for value in lines:
        value = CC.convert(html.unescape(value)).replace("\u200b", "").replace("\ufeff", "").replace("\xa0", " ")
        value = re.sub(r"https?://\S+", "", value)
        value = re.sub(r"\[编辑\]|\[編輯\]", "", value)
        value = MARKERS.sub("", value)
        value = re.sub(r"\s+", " ", value).strip()
        if not value or META.search(value):
            continue
        if STOP.fullmatch(value):
            break
        if value in seen and len(value) < 100:
            continue
        seen.add(value)
        result.append(value)
    while result and len(result[0]) < 12 and not re.search(r"[。！？；：]", result[0]):
        result.pop(0)
    return "\n\n".join(result).strip()


def drop_nonbody(container: BeautifulSoup) -> None:
    selectors = (
        "script style noscript img svg figure figcaption table sup sub pre code blockquote "
        ".mw-editsection .toc .navbox .noprint .printfooter .catlinks .metadata .infobox "
        ".ws-noexport .mw-references-wrap #comments .comments .comment .related .post-ratings "
        ".footer .sidebar .asset-footer .entry-footer .share .social"
    )
    for selector in selectors.split():
        for node in container.select(selector):
            node.decompose()


def make_slug(title: str) -> str:
    labels = {
        "政府工作报告": "gov_report",
        "最高人民法院": "court_report",
        "最高人民检察院": "procuratorate_report",
        "国民经济和社会发展计划": "development_plan",
        "预算执行情况": "budget_report",
        "武装力量": "armed_forces",
        "非洲": "africa_trade",
        "人权": "human_rights",
        "西藏": "tibet_development",
        "比特币": "bitcoin",
        "版权": "copyright",
        "程序员": "programmer",
        "效率": "efficiency",
    }
    prefix = next((v for k, v in labels.items() if k in title), "text")
    return f"{prefix}_{hashlib.md5(title.encode()).hexdigest()[:8]}"


def add_text(pool: list[dict], *, title: str, author: str, date: str, source_url: str,
             official_url: str, platform: str, genre: str, rights: str,
             license_url: str, text: str, notes: str) -> None:
    text = text.strip()
    if non_ws(text) < 700 or cjk(text) < 500:
        return
    if any(domain in source_url.lower() for domain in BAD_DOMAINS):
        return
    text_id = make_slug(title)
    existing = {row["text_id"] for row in pool}
    suffix = 2
    base = text_id
    while text_id in existing:
        text_id = f"{base}_{suffix}"
        suffix += 1
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
        "char_count": non_ws(text),
        "cjk_count": cjk(text),
        "paragraphs": len(text.split("\n\n")),
        "sha256": hashlib.sha256(re.sub(r"\s+", "", text).encode()).hexdigest(),
        "notes": notes,
    })


WIKI_API = "https://zh.wikisource.org/w/api.php"
PUBLIC_LICENSE = "Public domain: PRC Copyright Law Article 5 official document"
PUBLIC_LICENSE_URL = "https://www.ncac.gov.cn/xxfb/flfg/flfg_532/202103/t20210309_50530.html"

OFFICIAL_DOCS = [
    ("2013年中华人民共和国国务院政府工作报告", "中华人民共和国国务院", "政府工作回顾 / 政策评论", "https://www.gov.cn/2013lh/content_2356362.htm"),
    ("2013年中华人民共和国最高人民法院工作报告", "中华人民共和国最高人民法院", "司法工作回顾 / 制度评论", "https://www.court.gov.cn/"),
    ("2013年中华人民共和国最高人民检察院工作报告", "中华人民共和国最高人民检察院", "检察工作回顾 / 制度评论", "https://www.spp.gov.cn/"),
    ("关于2012年国民经济和社会发展计划执行情况与2013年国民经济和社会发展计划草案的报告", "国家发展和改革委员会", "经济发展评估 / 政策展望", "https://www.ndrc.gov.cn/"),
    ("关于2012年中央和地方预算执行情况与2013年中央和地方预算草案的报告", "中华人民共和国财政部", "财政执行评估 / 政策展望", "https://www.mof.gov.cn/"),
    ("中国武装力量的多样化运用", "国务院新闻办公室", "国防政策评论 / 白皮书", "https://www.gov.cn/zhengce/2013-04/16/content_2618505.htm"),
    ("中国与非洲的经贸合作（2013）", "国务院新闻办公室", "国际经贸回顾 / 白皮书", "https://www.gov.cn/zhengce/2013-08/29/content_2615771.htm"),
    ("2012年中国人权事业的进展", "国务院新闻办公室", "社会发展回顾 / 白皮书", "https://www.gov.cn/zhengce/2013-05/14/content_2615793.htm"),
    ("西藏的发展与进步", "国务院新闻办公室", "区域发展回顾 / 白皮书", "https://www.gov.cn/zhengce/2013-10/22/content_2615752.htm"),
]

REGIONAL_DOCS = [
    ("2013年北京市政府工作报告", "北京市人民政府", "https://www.beijing.gov.cn/"),
    ("2013年上海市政府工作报告", "上海市人民政府", "https://www.shanghai.gov.cn/"),
    ("2013年天津市政府工作报告", "天津市人民政府", "https://www.tj.gov.cn/"),
    ("2013年重庆市政府工作报告", "重庆市人民政府", "https://www.cq.gov.cn/"),
    ("2013年广东省政府工作报告", "广东省人民政府", "https://www.gd.gov.cn/"),
    ("2013年浙江省政府工作报告", "浙江省人民政府", "https://www.zj.gov.cn/"),
    ("2013年江苏省政府工作报告", "江苏省人民政府", "https://www.jiangsu.gov.cn/"),
    ("2013年山东省政府工作报告", "山东省人民政府", "http://www.shandong.gov.cn/"),
    ("2013年河南省政府工作报告", "河南省人民政府", "https://www.henan.gov.cn/"),
    ("2013年湖北省政府工作报告", "湖北省人民政府", "https://www.hubei.gov.cn/"),
    ("2013年湖南省政府工作报告", "湖南省人民政府", "https://www.hunan.gov.cn/"),
    ("2013年四川省政府工作报告", "四川省人民政府", "https://www.sc.gov.cn/"),
    ("2013年福建省政府工作报告", "福建省人民政府", "https://www.fujian.gov.cn/"),
    ("2013年安徽省政府工作报告", "安徽省人民政府", "https://www.ah.gov.cn/"),
    ("2013年河北省政府工作报告", "河北省人民政府", "https://www.hebei.gov.cn/"),
    ("2013年辽宁省政府工作报告", "辽宁省人民政府", "https://www.ln.gov.cn/"),
    ("2013年陕西省政府工作报告", "陕西省人民政府", "https://www.shaanxi.gov.cn/"),
    ("2013年云南省政府工作报告", "云南省人民政府", "https://www.yn.gov.cn/"),
    ("2013年广西壮族自治区政府工作报告", "广西壮族自治区人民政府", "http://www.gxzf.gov.cn/"),
    ("2013年内蒙古自治区政府工作报告", "内蒙古自治区人民政府", "https://www.nmg.gov.cn/"),
]


def wiki_title(query: str) -> str | None:
    response = fetch(WIKI_API, {
        "action": "query", "format": "json", "formatversion": 2,
        "titles": query, "redirects": 1,
    }, wiki=True).json()
    pages = response.get("query", {}).get("pages", [])
    if pages and not pages[0].get("missing"):
        return pages[0]["title"]
    response = fetch(WIKI_API, {
        "action": "query", "list": "search", "srsearch": f'"{query}"',
        "srlimit": 10, "format": "json", "formatversion": 2, "variant": "zh-hans",
    }, wiki=True).json()
    results = response.get("query", {}).get("search", [])
    for result in results:
        title = result["title"]
        if "2013" in query and "2013" not in title:
            continue
        return title
    return None


def parse_wiki_page(title: str) -> str:
    parsed = fetch(WIKI_API, {
        "action": "parse", "page": title, "prop": "text", "format": "json",
        "formatversion": 2, "disabletoc": 1, "disableeditsection": 1, "variant": "zh-hans",
    }, wiki=True).json()
    soup = BeautifulSoup(parsed["parse"]["text"], "lxml")
    container = soup.select_one(".mw-parser-output") or soup
    drop_nonbody(container)
    lines: list[str] = []
    started = False
    for element in container.find_all(["h2", "h3", "h4", "p", "li"]):
        value = CC.convert(element.get_text(" ", strip=True))
        if STOP.fullmatch(value):
            break
        if not started:
            started = bool(re.search(r"各位代表|前\s*言|过去五年|工作回顾|当前|一、|第一", value) or len(value) > 90)
            if not started:
                continue
        lines.append(value)
    return clean_lines(lines)


def collect_official(pool: list[dict]) -> None:
    documents = OFFICIAL_DOCS + [(q, a, "地方治理回顾 / 政策展望", u) for q, a, u in REGIONAL_DOCS]
    for query, author, genre, official_url in documents:
        try:
            title = wiki_title(query)
            if not title:
                print("OFFICIAL_NOT_FOUND", query)
                continue
            text = parse_wiki_page(title)
            source_url = "https://zh.wikisource.org/zh-hans/" + quote(title.replace(" ", "_"), safe="/:()（）")
            add_text(pool, title=query, author=author, date="2013", source_url=source_url,
                     official_url=official_url, platform="Wikisource / 国家机关公开文件",
                     genre="state official document / " + genre, rights=PUBLIC_LICENSE,
                     license_url=PUBLIC_LICENSE_URL, text=text,
                     notes=f"official_url={official_url}; Wikisource page={title}; main body only; Simplified Chinese conversion.")
            print("OFFICIAL", query, non_ws(text))
        except Exception as exc:
            print("OFFICIAL_FAIL", query, exc)


RUANYF_EXCLUDE = re.compile(
    r"详解|算法|JavaScript|Javascript|jQuery|Boyer|KMP|Event Loop|寄存器|Source Map|严格模式|"
    r"相似图片|TF-IDF|朴素贝叶斯|字符串匹配|CORS|RSA|CSS|HTTP|API|教程|安装|启动|GPG|PostgreSQL"
)
RUANYF_INCLUDE = re.compile(
    r"读后感|感想|用途|版权|垄断|分工|熵|心理|未来|当代中国|纪录片|创业|社会|制度|"
    r"苹果公司|美国枪击|开放|自由|互联网|人生|生活|民主|教育|经济|博客|比特币|货币|公司|产品|职业|梁漱溟"
)


def extract_ruanyf(soup: BeautifulSoup) -> tuple[str, str]:
    title_node = soup.select_one(".asset-name, .entry-title, article h1, #page-title, h1")
    content = soup.select_one(".asset-content, .entry-content, article, #main-content, #content")
    if not title_node or not content:
        return "", ""
    drop_nonbody(content)
    lines = []
    for element in content.find_all(["h2", "h3", "h4", "p", "li"]):
        if element.find_parent(["blockquote", "pre", "code", "table", "figure"]):
            continue
        value = element.get_text(" ", strip=True)
        if re.search(r"文档信息|版权声明|相关文章|留言（?\d*|上一篇|下一篇", value):
            break
        lines.append(value)
    return CC.convert(title_node.get_text(" ", strip=True)), clean_lines(lines)


def collect_ruanyf(pool: list[dict]) -> None:
    links: set[str] = set()
    for month in range(1, 13):
        try:
            soup = BeautifulSoup(fetch(f"https://www.ruanyifeng.com/blog/2013/{month:02d}/").text, "lxml")
            for anchor in soup.find_all("a", href=True):
                url = urljoin("https://www.ruanyifeng.com", anchor["href"])
                if re.search(r"/blog/2013/\d{2}/[^/?#]+\.html$", url):
                    links.add(url)
        except Exception as exc:
            print("RUANYF_ARCHIVE_FAIL", month, exc)
    for url in sorted(links):
        try:
            soup = BeautifulSoup(fetch(url).text, "lxml")
            title, text = extract_ruanyf(soup)
            if not title or RUANYF_EXCLUDE.search(title) or not RUANYF_INCLUDE.search(title):
                continue
            month = re.search(r"/blog/2013/(\d{2})/", url)
            date = "2013-" + month.group(1) if month else "2013"
            genre = "书评 / 影评 / 文化评论" if re.search(r"读后感|纪录片|电影|书", title) else "观点 / 科技与社会评论"
            add_text(pool, title=title, author="阮一峰", date=date, source_url=url,
                     official_url=url, platform="阮一峰的网络日志", genre=genre,
                     rights="CC BY-NC-ND 3.0 (site-level license)",
                     license_url="https://creativecommons.org/licenses/by-nc-nd/3.0/",
                     text=text,
                     notes="Site states 自由转载-非商用-非衍生-保持署名; main prose only; code, quotes, images, comments and back matter removed.")
        except Exception as exc:
            print("RUANYF_FAIL", url, exc)
    print("RUANYF_COUNT", len([x for x in pool if x["source_platform"] == "阮一峰的网络日志"]))


COOL_INCLUDE = re.compile(r"加班与效率|编程能力与编程年龄|面向对象的设计模式|环保.*百度|谎谬|至理名言|管理|职业|团队|开源|文化|思考|观点|设计")
COOL_EXCLUDE = re.compile(r"译文|翻译|摘录|教程|算法|技巧|二维码|Linux|Java|C语言|Lua|Shell|详解|原理")


def collect_coolshell(pool: list[dict]) -> None:
    repo = Path("/tmp/haoel")
    shutil.rmtree(repo, ignore_errors=True)
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/ghostincoolshell/haoel-articles.git", str(repo)], check=True)
    for path in sorted((repo / "blogs/rss2html2markdown").glob("2013-*.md")):
        title = re.sub(r"^2013-\d{1,2}-\d{1,2}\s+", "", path.stem)
        if not COOL_INCLUDE.search(title) or COOL_EXCLUDE.search(title):
            continue
        raw = path.read_text("utf-8", errors="ignore")
        raw = re.split(r"转载本站文章请注明作者和出处|请勿用于任何商业用途|相关文章", raw)[0]
        raw = re.sub(r"```.*?```", "", raw, flags=re.S)
        soup = BeautifulSoup(markdown.markdown(raw, extensions=["extra"]), "lxml")
        container = soup.body or soup
        drop_nonbody(container)
        text = clean_lines([e.get_text(" ", strip=True) for e in container.find_all(["h2", "h3", "h4", "p", "li"])])
        date_match = re.match(r"(2013-\d{1,2}-\d{1,2})", path.stem)
        date = date_match.group(1) if date_match else "2013"
        official_match = re.search(r"https://coolshell\.cn/articles/\d+\.html", raw)
        official_url = official_match.group(0) if official_match else "https://coolshell.cn/"
        source_url = (
            "https://github.com/ghostincoolshell/haoel-articles/blob/"
            "ba4cb2e19730d13ab92a1a0ced8c0798c6f32982/" + quote(str(path.relative_to(repo)), safe="/")
        )
        add_text(pool, title=title, author="陈皓 / CoolShell", date=date,
                 source_url=source_url, official_url=official_url,
                 platform="酷壳 CoolShell", genre="科技评论 / 职场评论",
                 rights="Author-permitted attribution; noncommercial only",
                 license_url="https://coolshell.cn/", text=text,
                 notes=f"Article footer permits redistribution with attribution and prohibits commercial use; official_url={official_url}; main prose only.")
    print("COOLSHELL_COUNT", len([x for x in pool if x["source_platform"] == "酷壳 CoolShell"]))


def paragraph_excerpt(item: dict, needed: int) -> dict | None:
    paragraphs: list[str] = []
    total = 0
    for paragraph in item["text"].split("\n\n"):
        size = non_ws(paragraph)
        if paragraphs and total + size > needed + 450:
            break
        paragraphs.append(paragraph)
        total += size
        if total >= needed - 250:
            break
    if total < 700:
        return None
    result = item.copy()
    result["text"] = "\n\n".join(paragraphs)
    result["text_id"] = item["text_id"] + "_excerpt"
    result["title"] = item["title"] + "（正文节选）"
    result["file_name"] = f"2013_O_{result['text_id']}_cleaned.txt"
    result["char_count"] = non_ws(result["text"])
    result["cjk_count"] = cjk(result["text"])
    result["paragraphs"] = len(paragraphs)
    result["sha256"] = hashlib.sha256(re.sub(r"\s+", "", result["text"]).encode()).hexdigest()
    result["notes"] += " Paragraph-boundary excerpt used only for bin balancing; no rewriting or padding."
    return result


def select_bins(pool: list[dict]) -> tuple[list[list[dict]], list[dict]]:
    unique: list[dict] = []
    hashes: set[str] = set()
    for item in pool:
        if item["sha256"] not in hashes:
            hashes.add(item["sha256"])
            unique.append(item)
    used: set[int] = set()
    bins: list[list[dict]] = []
    platforms = sorted({item["source_platform"] for item in unique})
    for bin_index in range(2):
        selected: list[dict] = []
        total = 0
        for platform in platforms:
            candidates = [x for x in unique if id(x) not in used and x["source_platform"] == platform]
            if candidates:
                candidates.sort(key=lambda x: x["char_count"])
                item = candidates[min(bin_index, len(candidates) - 1)]
                selected.append(item)
                used.add(id(item))
                total += item["char_count"]
        while total < TARGET - 650:
            remaining = [x for x in unique if id(x) not in used and total + x["char_count"] <= TARGET + 300]
            if not remaining:
                break
            item = max(remaining, key=lambda x: x["char_count"])
            selected.append(item)
            used.add(id(item))
            total += item["char_count"]
        if total < LOW:
            needed = TARGET - total
            candidates = sorted(
                [x for x in unique if id(x) not in used and x["char_count"] >= needed - 500],
                key=lambda x: abs(x["char_count"] - needed),
            )
            if candidates:
                excerpt = paragraph_excerpt(candidates[0], needed)
                if excerpt:
                    selected.append(excerpt)
                    used.add(id(candidates[0]))
        bins.append(selected)
    unused = [x for x in unique if id(x) not in used]
    return bins, unused


def write_outputs(bins: list[list[dict]], unused: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for bin_number, selected in enumerate(bins, 1):
        bin_name = f"2013_O_bin{bin_number:02d}"
        for item in selected:
            item["bin"] = bin_name
            (OUT / item["file_name"]).write_text(item["text"] + "\n", encoding="utf-8")
            row = {key: value for key, value in item.items() if key != "text"}
            row["index"] = len(rows) + 1
            rows.append(row)
        (OUT / f"{bin_name}_cleaned.txt").write_text(
            "\n\n".join(item["text"] for item in selected) + "\n", encoding="utf-8"
        )
    (OUT / "manifest.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = [
        "index", "text_id", "bin", "source_date", "title", "author", "source_platform", "genre",
        "source_url", "official_url", "copyright_status", "license_url", "file_name", "char_count",
        "cjk_count", "paragraphs", "sha256", "notes",
    ]
    with (OUT / "manifest.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)
    with (OUT / "excluded_candidates.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["title", "source_platform", "source_url", "reason"])
        for item in unused:
            writer.writerow([item["title"], item["source_platform"], item["source_url"], "licensed/open candidate not selected after balancing"])
        writer.writerow(["SCISCAN / 汉斯出版社", "excluded", "", "explicitly excluded by user"])
        writer.writerow(["知乎 / 豆瓣未授权全文", "excluded", "", "public readability is not redistribution permission"])

    stats: list[dict] = []
    issues: list[str] = []
    for bin_number, selected in enumerate(bins, 1):
        bin_name = f"2013_O_bin{bin_number:02d}"
        text = (OUT / f"{bin_name}_cleaned.txt").read_text("utf-8")
        stat = {
            "bin": bin_name,
            "non_whitespace_chars": non_ws(text),
            "cjk_chars": cjk(text),
            "files": len(selected),
            "platforms": sorted({item["source_platform"] for item in selected}),
        }
        stats.append(stat)
        if not LOW <= stat["non_whitespace_chars"] <= HIGH:
            issues.append(f"{bin_name} count outside range: {stat['non_whitespace_chars']}")
        if len(stat["platforms"]) < 2:
            issues.append(f"{bin_name} lacks source diversity")
    for row in rows:
        text = (OUT / row["file_name"]).read_text("utf-8")
        if re.search(r"\[(?:\d+|\d+[–—-]\d+)\]|[⁰¹²³⁴⁵⁶⁷⁸⁹]|参考文献|责任编辑[:：]|版权声明[:：]|文档信息|相关文章|留言（?\d*条", text):
            issues.append(row["text_id"] + " non-body marker")
        if row["source_date"][:4] != "2013" or any(domain in row["source_url"].lower() for domain in BAD_DOMAINS):
            issues.append(row["text_id"] + " source/year problem")
    qa = {
        "status": "PASS" if not issues else "FAIL",
        "year": YEAR,
        "target_per_bin": TARGET,
        "accepted_range": [LOW, HIGH],
        "bins": stats,
        "selected_documents": len(rows),
        "source_platforms": sorted({row["source_platform"] for row in rows}),
        "excluded_publishers": ["SCISCAN", "Hans Publishers / 汉斯出版社"],
        "issues": issues,
    }
    (OUT / "qa_report.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    report = ["# 2013_O Quality Assurance Report", "", f"**Status: {qa['status']}**", ""]
    for stat in stats:
        report.extend([
            f"## {stat['bin']}",
            f"- Non-whitespace characters: {stat['non_whitespace_chars']:,}",
            f"- CJK characters: {stat['cjk_chars']:,}",
            f"- Individual files: {stat['files']}",
            f"- Platforms: {', '.join(stat['platforms'])}", "",
        ])
    report.extend([
        "## Compliance",
        "- Main body only; title/byline/date, abstracts, figures/tables/captions, references, comments, footers and numeric citation markers removed.",
        "- No fabricated text, duplicated padding or paraphrasing.",
        "- SCISCAN, Hans Publishers and unlicensed Zhihu/Douban full text excluded.", "", "## Issues",
    ])
    report.extend([f"- {issue}" for issue in issues] if issues else ["- None detected."])
    (OUT / "QA_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        f"# 2013_O Corpus\n\nTwo Simplified Chinese Opinion/Commentary/Review bins. "
        f"Bin01: {stats[0]['non_whitespace_chars']:,}; Bin02: {stats[1]['non_whitespace_chars']:,} non-whitespace characters.\n",
        encoding="utf-8",
    )
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    if issues:
        raise SystemExit("QA failed")


def main() -> None:
    shutil.rmtree(OUT, ignore_errors=True)
    pool: list[dict] = []
    collect_official(pool)
    collect_ruanyf(pool)
    collect_coolshell(pool)
    total = sum(item["char_count"] for item in pool)
    print("POOL", len(pool), total, sorted({item["source_platform"] for item in pool}))
    if total < 225_000:
        raise SystemExit(f"insufficient pool: {total}")
    bins, unused = select_bins(pool)
    print("BIN_RAW", [sum(item["char_count"] for item in selected) for selected in bins])
    write_outputs(bins, unused)


if __name__ == "__main__":
    main()
