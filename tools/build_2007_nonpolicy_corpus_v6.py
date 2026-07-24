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
from urllib.parse import urljoin

from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("v5_builder", HERE / "build_2007_nonpolicy_corpus_v5.py")
v5 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v5
spec.loader.exec_module(v5)
b = v5.b

RUAN_TITLE_EXCLUDE = re.compile(
    r"故事|演讲|名言|语录|转贴|转帖|转载|译文|翻译|摘录|全文|照片|图片|词典|"
    r"辨析|语法|介词|标点符号|编码笔记|字符编码|RFC|Dublin Core|API$|代码|"
    r"免费网络资源|新闻奖|普利策|统计|数据排行|简历|讣告|去世|血$|诗$|"
    r"猛犸|干尸|面孔2007|病例|癌症病人|患者|煤矿|最脏的城市|工资条|"
    r"本人成分|新书《|传记|历史（|拉丁字母|英文字母|术语|定义|是什么$|"
    r"开幕词|致辞|声明|公告|通知|备忘录|清单|名单|年表|时间表|链接汇总",
    re.I,
)
RUAN_TITLE_INCLUDE = re.compile(
    r"评论|评析|影评|书评|感想|思考|观察|回顾|总结|推荐|比较|对比|体验|试用|"
    r"选择|未来|为什么|如何|怎样|是否|关于|谈|看法|杂感|印象|心得|经验|"
    r"旅行|游记|电影|纪录片|图书|读书|小说|音乐|博客|互联网|网络|网站|软件|"
    r"产品|媒体|新闻|大学|学校|职业|工作|生活|城市|文化|个人|自由|幸福|学习|"
    r"出版|市场|编辑|图书馆|商业|Google|微软|Web|BT|搜索|技术|经济学|设计",
    re.I,
)
EVALUATIVE = re.compile(
    r"我认为|我觉得|在我看来|我的看法|我想|我相信|我建议|我推荐|值得|不值得|"
    r"应该|不应该|优点|缺点|好处|问题在于|关键是|令人|可见|相比之下|总的来说|"
    r"总体而言|这说明|这意味着|我喜欢|我不喜欢|给我的印象|我的感受|我发现|"
    r"评价|评论|分析|观点|意义|趋势|未来|体验|试用|选择|反思|启示|原因是"
)
APPINN_TITLE_INCLUDE = re.compile(
    r"软件|工具|编辑器|播放器|输入法|浏览器|管理器|阅读器|查看器|启动|搜索|"
    r"桌面|网络|文件|笔记|截图|录屏|日历|地图|邮件|压缩|下载|备份|安全|"
    r"Firefox|Google|Windows|PDF|Word|Office|Linux|Mac|播放器|系统|热键|剪贴板",
    re.I,
)
APPINN_TITLE_EXCLUDE = re.compile(
    r"译文|翻译|转载|破解|绿色汉化|汉化版|序列号|注册码|新闻|发布$|更新$|升级$|"
    r"下载地址|源码|补丁|壁纸|图标组|主题包|月历|活动|公告|新年|节日|招聘",
    re.I,
)


def quality_score(title: str, text: str) -> int:
    score = len(EVALUATIVE.findall(text[:5000])) * 3
    score += len(re.findall(r"我|我的|我们", text[:3000]))
    if RUAN_TITLE_INCLUDE.search(title):
        score += 5
    if re.search(r"评论|评测|体验|试用|比较|感想|思考|观察|影评|书评", title):
        score += 8
    return score


def common_quality(title: str, text: str, raw: str, source: str) -> bool:
    n = b.count_chars(text)
    if n < 450 or n > 9_000:
        return False
    if v5.STRICT_FORBIDDEN.search(title + "\n" + text[:4000]) or v5.TITLE_BLOCK.search(title):
        return False
    if v5.REPOST_MARKERS.search(raw[:1800]) or v5.REPOST_MARKERS.search(text[:1200]):
        return False
    if source == "xbeta" and re.search(r"20(?:0[89]|1\d|2\d)年", text):
        return False
    return True


def collect_ruan_quality():
    repo = b.ROOT / ".cache" / "read"
    if repo.exists():
        shutil.rmtree(repo)
    repo.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/me115/read.git", str(repo)], check=True)
    root = repo / "ruanyifeng"
    files = sorted(root.rglob("2007*.rst"))
    out = []
    reasons = Counter()
    for p in files:
        raw = p.read_text(encoding="utf-8", errors="replace")
        title, url, text = b.clean_rst(raw)
        if not url or "/blog/2007/" not in url:
            reasons["wrong_year"] += 1
            continue
        if RUAN_TITLE_EXCLUDE.search(title):
            reasons["non_opinion_title"] += 1
            continue
        if not common_quality(title, text, raw, "ruanyifeng"):
            reasons["quality_or_policy"] += 1
            continue
        score = quality_score(title, text)
        # A clear commentary/review title needs fewer body markers; otherwise require sustained evaluation.
        if RUAN_TITLE_INCLUDE.search(title):
            if score < 7:
                reasons["weak_evaluation"] += 1
                continue
        elif score < 13:
            reasons["weak_evaluation"] += 1
            continue
        # Reject quotation-dominated pages and reference notes.
        quoted = sum(len(x) for x in re.findall(r"[“\"]([^”\"]{20,})[”\"]", text))
        if quoted > len(text) * 0.55:
            reasons["quotation_dominated"] += 1
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
                "Substantive wording unchanged; RST markup, title/byline display, raw URLs and non-body metadata removed."
            ),
        ))
    print("RUAN_QUALITY_SELECTED", len(out), sum(r.char_count for r in out), Counter(r.topic for r in out))
    print("RUAN_QUALITY_REASONS", reasons)
    for rec in sorted(out, key=lambda r: -r.char_count)[:12]:
        print("RUAN_LONG", rec.char_count, rec.title)
    return out


def archive_links(month: int):
    found = {}
    empty_pages = 0
    for page in range(1, 8):
        url = f"https://www.appinn.com/2007/{month:02d}/" + (f"page/{page}/" if page > 1 else "")
        try:
            r = b.S.get(url, timeout=45)
        except Exception as exc:
            print("APPINN_ARCHIVE_FAIL", url, repr(exc))
            break
        if r.status_code == 404:
            break
        if r.status_code != 200:
            print("APPINN_ARCHIVE_HTTP", r.status_code, url)
            break
        soup = BeautifulSoup(r.text, "lxml")
        before = len(found)
        selectors = ["h1.entry-title a", "h2.entry-title a", "h3.entry-title a", "article h2 a", "article h3 a", ".post-title a"]
        for sel in selectors:
            for a in soup.select(sel):
                href = urljoin(url, a.get("href", ""))
                title = a.get_text(" ", strip=True)
                if href.startswith("https://www.appinn.com/") and title:
                    found[href] = title
        if len(found) == before:
            empty_pages += 1
        else:
            empty_pages = 0
        if empty_pages >= 2:
            break
        time.sleep(0.5)
    return found


def extract_appinn_page(url: str, title_hint: str):
    r = b.S.get(url, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")
    soup = BeautifulSoup(r.text, "lxml")
    date_text = " ".join(x.get_text(" ", strip=True) for x in soup.select("time,.entry-date,.post-date,.date")[:3])
    author = ""
    for node in soup.select("[rel='author'],.author,.entry-author,.post-author"):
        t = node.get_text(" ", strip=True)
        if t and len(t) < 80:
            author = t
            break
    title_node = soup.select_one("h1.entry-title,h1.post-title,article h1,h1")
    title = title_node.get_text(" ", strip=True) if title_node else title_hint
    nodes = soup.select(".entry-content,.post-content,.post-body,article .content,article")
    best = ""
    for node in nodes:
        clone = BeautifulSoup(str(node), "lxml")
        for bad in clone.select("script,style,noscript,iframe,figure,figcaption,table,img,.wp-caption,.gallery,.sharedaddy,.comments,#comments,.comment,.related,.navigation,.download,.post-tags"):
            bad.decompose()
        text = b.normalize_text(clone.get_text("\n", strip=True))
        text = re.split(r"(?mi)^\s*(?:下载|软件下载|官方下载|相关链接|相关阅读|本文链接|标签[:：]|共有\s*\d+\s*条评论)\s*[:：]?", text)[0]
        if b.count_chars(text) > b.count_chars(best):
            best = text
    lines = best.splitlines()
    while lines and b.norm_title(lines[0]) == b.norm_title(title):
        lines.pop(0)
    return title, author or "小众软件编辑", date_text, b.normalize_text("\n".join(lines)), r.text


def collect_appinn_html():
    discovered = {}
    for month in range(1, 13):
        links = archive_links(month)
        print("APPINN_MONTH_LINKS", month, len(links))
        discovered.update(links)
    print("APPINN_DISCOVERED", len(discovered))
    title_candidates = []
    for url, title in discovered.items():
        if APPINN_TITLE_EXCLUDE.search(title):
            continue
        if not APPINN_TITLE_INCLUDE.search(title):
            continue
        title_candidates.append((url, title))
    print("APPINN_TITLE_CANDIDATES", len(title_candidates))
    out = []
    for url, hint in title_candidates[:90]:
        try:
            title, author, date_text, text, raw_html = extract_appinn_page(url, hint)
        except Exception as exc:
            print("APPINN_PAGE_FAIL", url, repr(exc))
            continue
        if date_text and "2007" not in date_text:
            continue
        if APPINN_TITLE_EXCLUDE.search(title):
            continue
        raw_text = BeautifulSoup(raw_html, "lxml").get_text("\n", strip=True)
        if re.search(r"\[译文\]|译者声明|原文链接|中文翻译|转载请保留此声明|本文转载", title + raw_text[:1600]):
            continue
        if not common_quality(title, text, raw_text, "appinn"):
            continue
        if quality_score(title, text) < 6 and not re.search(r"我|个人|觉得|发现|推荐|缺点|优点|相比|试用", text[:1600]):
            continue
        out.append(b.Rec(
            title=title,
            author=author,
            source="appinn",
            url=url,
            license_status="Attribution-NonCommercial-ShareAlike site terms; limited selected sample",
            license_url="https://www.appinn.com/copyright/",
            topic=b.topic_of(title, text),
            text=text,
            char_count=b.count_chars(text),
            notes=(
                "Official 2007 Appinn article page. Only a limited topic-diverse sample was selected, not a whole-site copy. "
                "Title/date/byline display, images, captions, download blocks, navigation, comments and related links removed."
            ),
        ))
        time.sleep(0.4)
    out.sort(key=lambda r: (-quality_score(r.title, r.text), -r.char_count))
    selected = []
    topics = Counter()
    chars = 0
    while out and len(selected) < 32 and chars < 38_000:
        out.sort(key=lambda r: (topics[r.topic], -quality_score(r.title, r.text), -r.char_count))
        rec = out.pop(0)
        selected.append(rec)
        topics[rec.topic] += 1
        chars += rec.char_count
    print("APPINN_HTML_SELECTED", len(selected), chars, topics)
    return selected


def collect_xbeta_quality():
    records = v5.collect_xbeta_relaxed()
    out = []
    for rec in records:
        if RUAN_TITLE_EXCLUDE.search(rec.title):
            continue
        if not common_quality(rec.title, rec.text, "", "xbeta"):
            continue
        if quality_score(rec.title, rec.text) < 6:
            continue
        out.append(rec)
    print("XBETA_QUALITY_SELECTED", len(out), sum(r.char_count for r in out))
    return out


def choose_balanced(records):
    by = defaultdict(list)
    for rec in records:
        by[rec.source].append(rec)
    for vals in by.values():
        vals.sort(key=lambda r: (-quality_score(r.title, r.text), -r.char_count))
    goals = {"ruanyifeng": 168_000, "appinn": 38_000, "xbeta": 14_000}
    selected, chosen = [], set()
    for source, goal in goals.items():
        pool = by.get(source, [])[:]
        total = 0
        topics = Counter()
        while pool and total < goal:
            pool.sort(key=lambda r: (topics[r.topic], -quality_score(r.title, r.text), -r.char_count))
            rec = pool.pop(0)
            selected.append(rec); chosen.add(id(rec)); total += rec.char_count; topics[rec.topic] += 1
    current = sum(r.char_count for r in selected)
    remaining = [r for r in records if id(r) not in chosen]
    target = b.TARGET_TOTAL - current
    if target > 0 and remaining:
        unit = 10
        tgt = round(target / unit)
        maxsum = tgt + 300
        reachable = {0: None}
        parent = {}
        for i, rec in enumerate(remaining):
            w = max(1, round(rec.char_count / unit))
            for s in sorted(list(reachable), reverse=True):
                ns = s + w
                if ns <= maxsum and ns not in reachable:
                    reachable[ns] = i; parent[(i, ns)] = s
        best = min(reachable, key=lambda s: abs(s - tgt))
        picks, s = [], best
        while s and reachable[s] is not None:
            i = reachable[s]; picks.append(i); s = parent[(i, s)]
        selected.extend(remaining[i] for i in reversed(picks))
    total = sum(r.char_count for r in selected)
    # Remove the least valuable item if total overshoots excessively and removal improves target distance.
    improved = True
    while improved:
        improved = False
        for rec in sorted(selected, key=lambda r: (quality_score(r.title, r.text), r.char_count)):
            nt = total - rec.char_count
            if nt >= 214_000 and abs(nt - b.TARGET_TOTAL) < abs(total - b.TARGET_TOTAL):
                selected.remove(rec); total = nt; improved = True; break
    print("QUALITY_FINAL_SELECTION", len(selected), total, Counter(r.source for r in selected), Counter(r.topic for r in selected))
    return selected


def partition_balanced(records):
    total = sum(r.char_count for r in records)
    target = total / 2
    records = sorted(records, key=lambda r: -r.char_count)
    a, c = [], []
    sa = sc = 0
    for rec in records:
        score_a = abs((sa + rec.char_count) - target) + abs((len(a) + 1) - (len(records) / 2)) * 80
        score_c = abs((sc + rec.char_count) - target) + abs((len(c) + 1) - (len(records) / 2)) * 80
        if score_a <= score_c:
            a.append(rec); sa += rec.char_count
        else:
            c.append(rec); sc += rec.char_count
    def obj(x, y):
        return abs(sum(r.char_count for r in x) - sum(r.char_count for r in y)) + abs(len(x) - len(y)) * 250
    for _ in range(60):
        old = obj(a, c)
        best = None; bestv = old
        for ra in a:
            for rc in c:
                na = sum(r.char_count for r in a) - ra.char_count + rc.char_count
                nc = total - na
                val = abs(na - nc) + abs(len(a) - len(c)) * 250
                if val < bestv:
                    bestv = val; best = (ra, rc)
        if not best:
            break
        ra, rc = best
        a.remove(ra); c.remove(rc); a.append(rc); c.append(ra)
    # Ensure each source represented in both bins when at least two records exist.
    for src in {r.source for r in records}:
        allsrc = [r for r in records if r.source == src]
        if len(allsrc) < 2:
            continue
        if not any(r.source == src for r in a):
            donor = min((r for r in c if r.source == src), key=lambda r: r.char_count)
            receiver = min(a, key=lambda r: abs(r.char_count - donor.char_count))
            c.remove(donor); a.remove(receiver); a.append(donor); c.append(receiver)
        if not any(r.source == src for r in c):
            donor = min((r for r in a if r.source == src), key=lambda r: r.char_count)
            receiver = min(c, key=lambda r: abs(r.char_count - donor.char_count))
            a.remove(donor); c.remove(receiver); c.append(donor); a.append(receiver)
    print("QUALITY_PARTITION", len(a), sum(r.char_count for r in a), len(c), sum(r.char_count for r in c))
    return a, c


b.collect_ruan = collect_ruan_quality
b.collect_moon = collect_appinn_html
b.collect_xbeta = collect_xbeta_quality
b.source_quota_select = choose_balanced
b.partition = partition_balanced

if __name__ == "__main__":
    b.main()
