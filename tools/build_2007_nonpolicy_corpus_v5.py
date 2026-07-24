from __future__ import annotations

import html
import importlib.util
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("v2_builder", HERE / "build_2007_nonpolicy_corpus_v2.py")
v2 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v2
spec.loader.exec_module(v2)
b = v2.b

STRICT_FORBIDDEN = re.compile(
    r"国家规划|政府工作报告|白皮书|国务院|部委|政策解读|五年规划|十一五|十二五|"
    r"立法|行政法规|法律制度|政治制度|人民民主专政|医疗保障制度|出版审查|审查制度|"
    r"土地制度|宏观调控|外交政策|财政政策|货币政策|政府支出|执政|党政|公安局|"
    r"征地|拆迁|条例|实施意见|指导意见|人大|政协|政党|民主制度|国家制度|"
    r"矿难|腐败|官员|外交|战争|示威|游行|政治|政府|法律|法院|判决|刑法|"
    r"医疗改革|住房政策|教育政策|污染政策|人口政策|互联网许可|新闻出版许可"
)

OPINION_TITLE = re.compile(
    r"评|评论|感想|思考|观察|回顾|总结|推荐|比较|对比|体验|试用|选择|未来|"
    r"为什么|如何|怎样|是否|谈|看|杂感|印象|心得|经验|旅行|游记|电影|纪录片|"
    r"图书|读书|小说|音乐|博客|互联网|网络|网站|软件|产品|媒体|新闻|大学|"
    r"学校|职业|工作|生活|城市|文化|个人|自由|幸福|学习|出版|市场|编辑|图书馆"
)
FIRST_PERSON = re.compile(r"我|我的|我们|认为|觉得|看来|感到|感觉|建议|推荐|印象|在我看来|我想|我相信")
REPOST_MARKERS = re.compile(r"^(?:转载|译文|翻译|摘译|原文作者|译者|本文译自|转贴|转帖)|作者[:：].{0,12}(?:投稿|翻译)", re.M)
TITLE_BLOCK = re.compile(
    r"政府|国家|政治|法律|制度|政策|官员|民主|外交|战争|矿难|房地产|房价|医疗保障|"
    r"医保|土地所有权|网络许可|人民民主专政|拆迁|污染|财政|税收|汇率|央行|"
    r"就业法|价格管制|互联网出版许可|审查|公民权利|党|选举"
)


def safe_post(title: str, text: str, raw: str = "", source: str = "") -> bool:
    n = b.count_chars(text)
    if n < 350 or n > 25_000:
        return False
    if STRICT_FORBIDDEN.search(title + "\n" + text[:3500]) or TITLE_BLOCK.search(title):
        return False
    if REPOST_MARKERS.search(raw[:1500]) or REPOST_MARKERS.search(text[:1000]):
        return False
    if source == "xbeta" and re.search(r"20(?:0[89]|1\d|2\d)年", text):
        return False
    if not (OPINION_TITLE.search(title) or FIRST_PERSON.search(text[:1600])):
        return False
    # Reject code-heavy tutorials and link compilations.
    lines = [x for x in text.splitlines() if x.strip()]
    if lines:
        codeish = sum(bool(re.search(r"[{};]|^\s*(?:function|class|var |SELECT |INSERT |<\w+|/\*)", x)) for x in lines)
        if codeish / len(lines) > 0.18:
            return False
    if len(re.findall(r"https?://", raw)) > 35 and n < 5000:
        return False
    return True


def collect_ruan_all():
    repo = b.ROOT / ".cache" / "read"
    if repo.exists():
        shutil.rmtree(repo)
    repo.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/me115/read.git", str(repo)], check=True)
    root = repo / "ruanyifeng"
    files = sorted(root.rglob("2007*.rst"))
    print("RUAN_2007_FILES", len(files))
    out = []
    excluded = Counter()
    for p in files:
        raw = p.read_text(encoding="utf-8", errors="replace")
        title, url, text = b.clean_rst(raw)
        if not url or "/blog/2007/" not in url:
            excluded["url_year"] += 1
            continue
        if not safe_post(title, text, raw, "ruanyifeng"):
            if TITLE_BLOCK.search(title) or STRICT_FORBIDDEN.search(title + text[:3500]):
                excluded["policy_governance"] += 1
            elif REPOST_MARKERS.search(raw[:1500]) or REPOST_MARKERS.search(text[:1000]):
                excluded["repost_translation"] += 1
            elif b.count_chars(text) < 350:
                excluded["short"] += 1
            else:
                excluded["not_opinion_or_code"] += 1
            continue
        out.append(b.Rec(
            title=title,
            author="阮一峰",
            source="ruanyifeng",
            url=url,
            license_status="CC BY-NC-ND 3.0; verbatim noncommercial research extract",
            license_url="https://www.ruanyifeng.com/blog/",
            topic=b.topic_of(title, text),
            text=text,
            char_count=b.count_chars(text),
            notes=(
                "Public RST mirror used only for technical retrieval; official 2007 article URL retained. "
                "The substantive wording is unchanged; RST markup, title/byline display, raw URLs and non-body metadata were removed."
            ),
        ))
    print("RUAN_ALL_SELECTED", len(out), sum(r.char_count for r in out), Counter(r.topic for r in out))
    print("RUAN_EXCLUSION_COUNTS", excluded)
    return out


def clean_appinn_html(rendered: str):
    soup = BeautifulSoup(html.unescape(rendered or ""), "lxml")
    for bad in soup.select("script,style,noscript,iframe,figure,figcaption,table,img,.wp-caption,.gallery,.sharedaddy,.sd-sharing-enabled"):
        bad.decompose()
    text = soup.get_text("\n", strip=True)
    text = re.split(r"(?mi)^\s*(?:下载地址|软件下载|官方网站|相关链接|相关阅读|本文链接|小众软件|©)\s*[:：]?", text)[0]
    text = b.normalize_text(text)
    return text


def appinn_user_name(user_id, cache):
    if user_id in cache:
        return cache[user_id]
    try:
        r = b.S.get(f"https://www.appinn.com/wp-json/wp/v2/users/{user_id}", timeout=45)
        if r.status_code == 200:
            cache[user_id] = html.unescape(r.json().get("name") or "小众软件编辑")
        else:
            cache[user_id] = "小众软件编辑"
    except Exception:
        cache[user_id] = "小众软件编辑"
    return cache[user_id]


def collect_appinn():
    endpoint = "https://www.appinn.com/wp-json/wp/v2/posts"
    params = {
        "after": "2007-01-01T00:00:00",
        "before": "2008-01-01T00:00:00",
        "per_page": 100,
        "page": 1,
        "orderby": "date",
        "order": "asc",
        "_fields": "id,date,link,title,content,author",
    }
    posts = []
    while params["page"] <= 10:
        try:
            r = b.S.get(endpoint, params=params, timeout=60)
        except Exception as exc:
            print("APPINN_API_FAIL", repr(exc))
            break
        if r.status_code == 400 and "rest_post_invalid_page_number" in r.text:
            break
        if r.status_code != 200:
            print("APPINN_API_HTTP", r.status_code, r.text[:300])
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        total_pages = int(r.headers.get("X-WP-TotalPages", params["page"]))
        if params["page"] >= total_pages:
            break
        params["page"] += 1
        time.sleep(1)
    print("APPINN_2007_POSTS", len(posts))
    users = {}
    out = []
    for post in posts:
        title = BeautifulSoup(post.get("title", {}).get("rendered", ""), "lxml").get_text(" ", strip=True)
        rendered = post.get("content", {}).get("rendered", "")
        text = clean_appinn_html(rendered)
        raw = BeautifulSoup(rendered, "lxml").get_text("\n", strip=True)
        if not safe_post(title, text, raw, "appinn"):
            continue
        # Appinn permits personal noncommercial attributed sharing but disallows wholesale replication.
        # Keep a limited, topic-diverse 2007 sample rather than the whole archive.
        author = appinn_user_name(post.get("author"), users)
        out.append(b.Rec(
            title=title,
            author=author,
            source="appinn",
            url=post.get("link", ""),
            license_status="CC BY-NC-SA-style site terms; selected sample only, no whole-site replication",
            license_url="https://www.appinn.com/copyright/",
            topic=b.topic_of(title, text),
            text=text,
            char_count=b.count_chars(text),
            notes=(
                "Retrieved through the public WordPress REST API. Selected from 2007 software-review/editorial posts only; this corpus does not reproduce the full Appinn archive. "
                "Images, captions, download blocks, navigation and comments were removed."
            ),
        ))
    # Limit Appinn to a diverse sample, respecting the site's no-bulk-copy statement.
    out.sort(key=lambda r: (-r.char_count, r.title))
    selected = []
    topic_counts = Counter()
    source_chars = 0
    while out and len(selected) < 35 and source_chars < 45_000:
        out.sort(key=lambda r: (topic_counts[r.topic], -r.char_count))
        rec = out.pop(0)
        selected.append(rec)
        topic_counts[rec.topic] += 1
        source_chars += rec.char_count
    print("APPINN_SELECTED", len(selected), source_chars, topic_counts)
    return selected


def collect_xbeta_relaxed():
    records = v2.collect_xbeta_v2()
    # Restore author-original articles excluded only because the old routine reused the stricter min/body check.
    pairs = list(b.XBETA_DIRECT)
    pairs += [(t, u) for t, u in b.xbeta_index_links().items()]
    used_urls = {r.url for r in records}
    for title, url in pairs:
        if url in used_urls:
            continue
        try:
            text = b.html_main(url, title)
        except Exception:
            continue
        if safe_post(title, text, "", "xbeta"):
            records.append(b.Rec(
                title=title,
                author="善用佳软（张玉新/xbeta）",
                source="xbeta",
                url=url,
                license_status="CC0 / Public Domain for xbeta-original content",
                license_url="https://xbeta.info/about",
                topic=b.topic_of(title, text),
                text=text,
                char_count=b.count_chars(text),
                notes=(
                    "Official xbeta page; author-original 2007 review/commentary. Excluded if later-year substantive revisions were detected. "
                    "Markup, images, update metadata and navigation removed."
                ),
            ))
    print("XBETA_RELAXED_SELECTED", len(records), sum(r.char_count for r in records))
    return records


def select_records(records):
    by = defaultdict(list)
    for r in records:
        by[r.source].append(r)
    for vals in by.values():
        vals.sort(key=lambda r: (-r.char_count, r.title))
    goals = {"ruanyifeng": 175_000, "appinn": 35_000, "xbeta": 12_000}
    selected = []
    chosen = set()
    for source, goal in goals.items():
        pool = by.get(source, [])[:]
        total = 0
        topics = Counter()
        while pool and total < goal:
            pool.sort(key=lambda r: (topics[r.topic], -r.char_count))
            rec = pool.pop(0)
            selected.append(rec)
            chosen.add(id(rec))
            topics[rec.topic] += 1
            total += rec.char_count
    current = sum(r.char_count for r in selected)
    remaining = [r for r in records if id(r) not in chosen]
    target = b.TARGET_TOTAL - current
    if target > 0 and remaining:
        unit = 25
        tgt = round(target / unit)
        maxsum = tgt + 400
        reachable = {0: None}
        parent = {}
        for i, rec in enumerate(remaining):
            w = max(1, round(rec.char_count / unit))
            for s in sorted(list(reachable), reverse=True):
                ns = s + w
                if ns <= maxsum and ns not in reachable:
                    reachable[ns] = i
                    parent[(i, ns)] = s
        best = min(reachable, key=lambda s: abs(s - tgt))
        picks = []
        s = best
        while s and reachable[s] is not None:
            i = reachable[s]
            picks.append(i)
            s = parent[(i, s)]
        selected.extend(remaining[i] for i in reversed(picks))
    total = sum(r.char_count for r in selected)
    if total < 216_000:
        for r in sorted((r for r in records if r not in selected), key=lambda x: x.char_count):
            selected.append(r)
            total += r.char_count
            if total >= 216_000:
                break
    print("FINAL_SELECTION_PREPARTITION", len(selected), total, Counter(r.source for r in selected))
    return selected


b.safe = safe_post
b.collect_ruan = collect_ruan_all
b.collect_moon = collect_appinn
b.collect_xbeta = collect_xbeta_relaxed
b.source_quota_select = select_records
b.partition = v2.dp_partition

if __name__ == "__main__":
    b.main()
