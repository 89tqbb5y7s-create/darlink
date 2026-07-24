from __future__ import annotations

import hashlib
import html
import json
import math
import random
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "corpus_build"
TEXTS = OUT / "texts"
TARGET_TOTAL = 220_000
TARGET_BIN = 110_000
UA = "Mozilla/5.0 (compatible; academic-corpus-builder/1.0; +noncommercial-research)"
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5"})

FORBIDDEN = re.compile(
    r"国家规划|政府工作报告|白皮书|国务院|部委|政策解读|五年规划|十一五|十二五|"
    r"立法|行政法规|法律制度|政治制度|人民民主专政|医疗保障制度|出版审查|审查制度|"
    r"土地制度|宏观调控|外交政策|财政政策|货币政策|政府支出|执政|党政|公安局|"
    r"征地|拆迁|条例|办法|通知|实施意见|指导意见"
)

RUAN_PATHS = [
    "notes/200710_internal_connections_in_lust_caution.rst",
    "notes/200710_ig_nobel_prize_2007.rst",
    "notes/200707_my_dalian_trip_part_i.rst",
    "notes/200707_my_dalian_trip_part_ii.rst",
    "notes/200705_night_on_the_grass.rst",
    "notes/200703_output_welfare_and_happiness.rst",
    "notes/200703_hedonomics.rst",
    "notes/200703_children_of_men.rst",
    "notes/200703_notes_on_hu_shih_oral_autobiography.rst",
    "notes/200702_how_to_write_vernacular_chinese.rst",
    "notes/200702_a_kind_of_personal_nature_classification.rst",
    "notes/200702_beijing_winter.rst",
    "notes/200701_kenny.rst",
    "notes/200701_nougat.rst",
    "notes/200701_the_painted_veil.rst",
    "notes/200711_waitress.rst",
    "notes/200704_my_second_book.rst",
    "notes/200703_felix_alder.rst",
    "misc/200712_50_top_10_lists_of_2007.rst",
    "misc/200711_you_by_huang_shujun.rst",
    "misc/200711_the_hoax.rst",
    "misc/200710_laptop_recommendation.rst",
    "misc/200709_xiangbala_postman.rst",
    "misc/200709_the_reaping_surfs_up_sunshine.rst",
    "misc/200709_magic_tap.rst",
    "misc/200709_web_experiment_of_candid_snapshot.rst",
    "misc/200708_open_library.rst",
    "misc/200707_1408.rst",
    "misc/200707_suzhou_river.rst",
    "misc/200707_biggest_carp_in_the_world.rst",
    "misc/200707_zodiac.rst",
    "misc/200707_2007_usa_new_movie_recommendation_list.rst",
    "misc/200706_some_thoughts_on_my_trip_of_dalian.rst",
    "misc/200706_my_live_blogging_experiment.rst",
    "misc/200705_campus_in_spring.rst",
    "misc/200705_interesting_electronic_products.rst",
    "misc/200704_memories_of_matsuko.rst",
    "misc/200704_never_too_old_to_learn.rst",
    "misc/200704_moodori.rst",
    "misc/200704_wordpress_vs_movable_type.rst",
    "misc/200704_impossible_is_0.rst",
    "misc/200703_whats_a_healthy_family.rst",
    "misc/200703_new_library_of_shufe.rst",
    "misc/200702_popular_folk_sayings_in_2007.rst",
    "misc/200702_internet_slang.rst",
    "misc/200702_interesting_clocks.rst",
    "misc/200702_a_bookstore_beside_my_school.rst",
    "misc/200701_the_unbearable_heaviness_of_being.rst",
    "misc/200701_just_a_song_before_i_go.rst",
    "opinions/200712_2007_my_blogging_summary.rst",
    "opinions/200712_some_thoughts_about_china_book_market.rst",
    "opinions/200710_daniele_mattioli.rst",
    "opinions/200710_news_n_editorial.rst",
    "opinions/200708_where_are_the_medical_graduates.rst",
    "opinions/200705_how_high_is_the_profit_of_textbook.rst",
    "opinions/200705_a_pair_of_misable_pandas.rst",
    "opinions/200705_self_and_freedom.rst",
    "opinions/200704_guo_taiming.rst",
    "opinions/200703_blood_diamond.rst",
    "opinions/200702_the_benefits_of_giving_a_speech.rst",
    "essays/200712_interest_rate_and_job.rst",
    "essays/200703_where_the_hell_is_matt.rst",
    "sci-tech/200708_photosynth.rst",
    "sci-tech/200701_a_land_we_call_homeland.rst",
]

MOON_TITLES = [
    "Picasa Web Albums的发展前景分析",
    "照片共享服务panoramio和flickr的对比评测",
    "中文Google地图的发展前景",
    "Google地图的应用开发分析",
    "Google Group网上论坛的疑惑",
    "Google Adsense和百度联盟的比较",
    "腾讯QQ拼音输入法试用",
    "网站登录的加密传输安全",
    "使用OpenDNS解决DNS域名劫持",
    "DreamHost的续费策略",
    "Google Earth能否实现“卫星实时监控”",
    "生化危机4和系列游戏杂感",
    "深圳世界之窗游记",
    "湖南凤凰古城游记",
    "从袁家界到芙蓉镇",
    "张家界金鞭溪游记",
    "自我激励与团队沟通的培训",
    "Gmail IMAP的应用技巧",
    "我无法访问的国外优秀网站",
    "Google、雅虎和微软被域名劫持的后话",
    "FeedBurner的邮件订阅功能试用",
    "中国网上银行系统安全性分析",
    "电信屏蔽eMule了吗",
    "百度也恶搞？",
    "攀比深圳：广州开始搞浮夸风了",
    "Google Earth中文版试用",
    "Google拼音输入法试用",
    "Google Reader离线版试用",
    "Flickr中文界面试用",
    "Google街景地图试用",
    "共享软件的开发和营销策略",
    "软件商业模式的发展与2.0时代",
    "Google搜索在工作上的应用技巧",
    "使用Google进行时间管理",
]

XBETA_DIRECT = [
    ("screen2exe:小巧的录屏软件", "https://xbeta.info/screen2exe%E5%B0%8F%E5%B7%A7%E7%9A%84%E5%BD%95%E5%B1%8F%E8%BD%AF%E4%BB%B6.htm"),
    ("代替windows计算器的增强软件", "https://xbeta.info/calc.htm"),
    ("Sandboxie：在沙盘中运行程序", "https://xbeta.info/sandboxie.htm"),
    ("寻找最好的笔记软件:三强篇", "https://xbeta.info/evernote-mybase-surfulater.htm"),
    ("寻找最好的笔记软件:梦想篇", "https://xbeta.info/best-note-tool-4.htm"),
    ("最全面实用的文字编排利器：文本整理器V3.0", "https://xbeta.info/%E6%9C%80%E5%85%A8%E9%9D%A2%E5%AE%9E%E7%94%A8%E7%9A%84%E6%96%87%E5%AD%97%E7%BC%96%E6%8E%92%E5%88%A9%E5%99%A8%EF%BC%9A%E6%96%87%E6%9C%AC%E6%95%B4%E7%90%86%E5%99%A8v30.htm"),
]
XBETA_WANTED = [
    "高效文本编辑的7个习惯",
    "图解Total Commander 7.0之22项更新与改进",
    "用免费软件替代MS Project续篇",
    "如何成为优秀的软件博客",
    "高效使用软件的3项必备因素",
    "WinRAR vs WinZip vs 7-Zip",
    "合理使用AutoHotKey+StrokeIt",
    "简评主流免费截屏软件的优缺点",
    "能否代替MS Office？深入试用WPS2007",
    "寻找最好的笔记软件:海选篇",
    "点评“最好的300款免费软件”",
]

@dataclass
class Rec:
    title: str
    author: str
    source: str
    url: str
    license_status: str
    license_url: str
    topic: str
    text: str
    char_count: int
    file_name: str = ""
    bin: str = ""
    text_id: str = ""
    notes: str = ""


def norm_title(s: str) -> str:
    s = unicodedata.normalize("NFKC", html.unescape(s or ""))
    s = re.sub(r"[\s\-—–_:：,，。.!！?？'\"“”‘’()（）\[\]【】]+", "", s)
    return s.lower()


def count_chars(s: str) -> int:
    return len(re.sub(r"\s+", "", s))


def slug(s: str) -> str:
    ascii_bits = re.findall(r"[A-Za-z0-9]+", s)
    if ascii_bits:
        v = "_".join(ascii_bits[:5]).lower()
    else:
        v = hashlib.sha1(s.encode()).hexdigest()[:10]
    return re.sub(r"[^a-z0-9_]+", "_", v).strip("_")[:60] or hashlib.sha1(s.encode()).hexdigest()[:10]


def get(url: str, attempts: int = 4) -> requests.Response:
    last = None
    for i in range(attempts):
        try:
            r = S.get(url, timeout=35)
            if r.status_code == 200 and len(r.content) > 100:
                r.encoding = r.apparent_encoding or r.encoding
                return r
            last = RuntimeError(f"HTTP {r.status_code} {url}")
        except Exception as e:
            last = e
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(str(last))


def clean_rst(raw: str) -> tuple[str, str, str]:
    raw = raw.replace("\r\n", "\n")
    url_m = re.search(r"https?://www\.ruanyifeng\.com/blog/[^>`\s]+", raw)
    url = url_m.group(0) if url_m else ""
    lines = raw.splitlines()
    title = ""
    for i, line in enumerate(lines):
        t = line.strip()
        if not t or t.startswith(".. _"):
            continue
        if i + 1 < len(lines) and re.fullmatch(r"[=\-~`^:#*+]{3,}", lines[i + 1].strip()):
            title = t
            break
    cut = raw.split(".. note::", 1)[0]
    # Drop document header through first source URL line.
    if url:
        pos = cut.find(url)
        if pos >= 0:
            nl = cut.find("\n", pos)
            cut = cut[nl + 1:] if nl >= 0 else ""
    cut = re.sub(r"(?ms)^\.\. (?:image|figure|raw|code-block)::.*?(?=\n\S|\Z)", "", cut)
    cut = re.sub(r"(?ms)^\s*:(?:alt|width|height|align|target):.*$", "", cut)
    cut = re.sub(r"`([^`<>]+?)\s*<https?://[^>]+>`__", r"\1", cut)
    cut = re.sub(r"`([^`]+?)`__", r"\1", cut)
    cut = re.sub(r"https?://\S+", "", cut)
    cut = cut.replace("\\ ", " ").replace("\\", "")
    cut = cut.replace("**", "").replace("*", "")
    cut = re.sub(r"(?m)^\s*[=\-~`^:#*+]{3,}\s*$", "", cut)
    cut = re.sub(r"(?m)^\s*\(完\)\s*$", "", cut)
    cut = re.split(r"(?m)^\s*\[相关链接\]\s*$", cut)[0]
    cut = re.sub(r"(?m)^\s*\|\s?", "", cut)
    cut = re.sub(r"(?m)^\s*\.\.\s+.*$", "", cut)
    cut = html.unescape(cut)
    text = normalize_text(cut)
    return title.strip(), url, text


def normalize_text(s: str) -> str:
    s = unicodedata.normalize("NFC", html.unescape(s))
    s = s.replace("\xa0", " ").replace("\u3000", " ")
    s = re.sub(r"\[(?:\d+|[a-zA-Z])\]", "", s)
    s = re.sub(r"(?<=\w)[¹²³⁴⁵⁶⁷⁸⁹⁰]+", "", s)
    lines = []
    for line in s.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if re.fullmatch(r"(?:上一篇|下一篇|返回首页|发表评论|分享到).{0,30}", line):
            continue
        lines.append(line)
    s = "\n".join(lines).strip()
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s


def topic_of(title: str, text: str) -> str:
    t = title + text[:400]
    rules = [
        ("software_review", r"软件|输入法|WordPress|WPS|压缩|录屏|计算器|笔记|剪贴板|浏览器|程序"),
        ("internet_commentary", r"Google|百度|网站|博客|互联网|Web|DNS|Flickr|Picasa|网络"),
        ("film_review", r"电影|纪录片|影片|观后|评分|影评|生化危机|色戒|血钻"),
        ("book_culture", r"图书|书店|读书|出版|胡适|白话文|小说|书评"),
        ("travel_urban", r"游记|旅行|大连|凤凰|张家界|深圳|北京|校园|城市"),
        ("career_learning", r"职业|就业|培训|演讲|学习|团队|工作|成长"),
        ("media_culture", r"新闻|编辑|媒体|音乐|流行语|方言|文化"),
    ]
    for name, pat in rules:
        if re.search(pat, t, re.I):
            return name
    return "general_commentary"


def safe(title: str, text: str, source: str) -> bool:
    if not text or count_chars(text) < 650:
        return False
    if count_chars(text) > 30_000:
        return False
    if FORBIDDEN.search(title + "\n" + text[:2500]):
        return False
    if re.search(r"(?:转载|译文|翻译：|原文作者|新闻稿)", title + text[:500]):
        return False
    if source == "xbeta" and re.search(r"20(?:0[89]|1\d|2\d)年", text):
        return False
    return True


def html_main(url: str, title_hint: str) -> str:
    soup = BeautifulSoup(get(url).text, "lxml")
    for bad in soup.select("script,style,noscript,nav,footer,aside,form,iframe,.comments,#comments,.comment,.related,.post-related,.share,.social,.navigation,.breadcrumb,figure,figcaption,table"):
        bad.decompose()
    sels = [
        ".entry-content", ".post-body", ".post-content", ".article-content", ".article-body",
        ".postBody", ".logbody", "article .content", "article", "main"
    ]
    nodes = []
    for sel in sels:
        nodes.extend(soup.select(sel))
    h = None
    nt = norm_title(title_hint)
    for tag in soup.find_all(["h1", "h2", "h3"]):
        if nt and (nt == norm_title(tag.get_text(" ", strip=True)) or nt in norm_title(tag.get_text(" ", strip=True))):
            h = tag
            break
    if h:
        p = h
        for _ in range(5):
            p = p.parent
            if p:
                nodes.append(p)
    best = ""
    best_score = -10**9
    seen = set()
    for node in nodes:
        key = id(node)
        if key in seen:
            continue
        seen.add(key)
        clone = BeautifulSoup(str(node), "lxml")
        for bad in clone.select("script,style,noscript,nav,footer,aside,form,iframe,.comments,#comments,.comment,.related,.post-related,.share,.social,.navigation,.breadcrumb,figure,figcaption,table,img"):
            bad.decompose()
        text = normalize_text(clone.get_text("\n", strip=True))
        # Remove title and common metadata at the beginning.
        ls = text.splitlines()
        while ls and (norm_title(ls[0]) == nt or re.search(r"^(?:20)?07[-年/.]|作者[:：]|分类[:：]|评论[:：]|浏览[:：]", ls[0])):
            ls.pop(0)
        text = normalize_text("\n".join(ls))
        text = re.split(r"(?m)^\s*(?:相关文章|相关阅读|标签[:：]|评论列表|发表评论|上一篇|下一篇)\s*$", text)[0]
        links = len(clone.find_all("a"))
        score = count_chars(text) - links * 8
        if title_hint and title_hint in text[:200]:
            score -= 200
        if score > best_score:
            best, best_score = text, score
    return best


def collect_ruan() -> list[Rec]:
    repo = ROOT / ".cache" / "read"
    if repo.exists():
        shutil.rmtree(repo)
    repo.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/me115/read.git", str(repo)], check=True)
    out = []
    for rel in RUAN_PATHS:
        p = repo / "ruanyifeng" / rel
        if not p.exists():
            print("RUAN_MISSING", rel)
            continue
        title, url, text = clean_rst(p.read_text(encoding="utf-8", errors="replace"))
        if safe(title, text, "ruanyifeng"):
            out.append(Rec(title, "阮一峰", "ruanyifeng", url,
                           "CC BY-NC-ND 3.0; verbatim noncommercial research extract",
                           "https://www.ruanyifeng.com/blog/", topic_of(title, text), text, count_chars(text),
                           notes="Mirror used only for technical retrieval; official article URL retained. Substantive wording unchanged; markup and non-body metadata removed."))
        else:
            print("RUAN_EXCLUDED", title, count_chars(text))
    return out


def moon_urls() -> dict[str, str]:
    wanted = {norm_title(x): x for x in MOON_TITLES}
    found = {}
    for m in range(1, 13):
        url = f"https://www.williamlong.info/date/2007-{m:02d}.html"
        try:
            soup = BeautifulSoup(get(url).text, "lxml")
        except Exception as e:
            print("MOON_ARCHIVE_FAIL", url, e)
            continue
        for a in soup.find_all("a", href=True):
            n = norm_title(a.get_text(" ", strip=True))
            if n in wanted:
                found[wanted[n]] = urljoin(url, a["href"])
    return found


def collect_moon() -> list[Rec]:
    found = moon_urls()
    out = []
    for title in MOON_TITLES:
        url = found.get(title)
        if not url:
            print("MOON_NOT_FOUND", title)
            continue
        try:
            text = html_main(url, title)
        except Exception as e:
            print("MOON_FAIL", title, e)
            continue
        if safe(title, text, "moonlight"):
            out.append(Rec(title, "月光", "moonlight", url,
                           "CC BY-NC-SA (署名-非商业用途-相同方式共享)",
                           "https://www.williamlong.info/archives/480.html", topic_of(title, text), text, count_chars(text),
                           notes="Official 2007 article page. Main prose retained; title/byline/date, images, navigation, comments and related links removed."))
        else:
            print("MOON_EXCLUDED", title, count_chars(text))
    return out


def xbeta_index_links() -> dict[str, str]:
    found = {}
    try:
        soup = BeautifulSoup(get("https://xbeta.info/index-1").text, "lxml")
    except Exception as e:
        print("XBETA_INDEX_FAIL", e)
        return found
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        n = norm_title(text)
        for wanted in XBETA_WANTED:
            nw = norm_title(wanted)
            if nw and (nw in n or n in nw) and "xbeta.info" in urljoin("https://xbeta.info", a["href"]):
                found.setdefault(wanted, urljoin("https://xbeta.info", a["href"]))
    return found


def collect_xbeta() -> list[Rec]:
    pairs = list(XBETA_DIRECT)
    pairs += [(t, u) for t, u in xbeta_index_links().items()]
    out = []
    used = set()
    for hint, url in pairs:
        if url in used:
            continue
        used.add(url)
        try:
            text = html_main(url, hint)
            soup = BeautifulSoup(get(url).text, "lxml")
            page_title = (soup.find("h1") or soup.find("title"))
            title = page_title.get_text(" ", strip=True) if page_title else hint
            title = re.sub(r"\s*[|–—-]\s*善用佳软.*$", "", title).strip()
        except Exception as e:
            print("XBETA_FAIL", hint, e)
            continue
        if safe(title, text, "xbeta"):
            out.append(Rec(title, "善用佳软（张玉新/xbeta）", "xbeta", url,
                           "CC0 / Public Domain for xbeta-original content",
                           "https://xbeta.info/about", topic_of(title, text), text, count_chars(text),
                           notes="Official xbeta page; author-original 2007 review/commentary. Excluded if later-year substantive revisions were detected. Markup, images, update metadata and navigation removed."))
        else:
            print("XBETA_EXCLUDED", title, count_chars(text))
    return out


def dedupe(records: list[Rec]) -> list[Rec]:
    out, hashes = [], set()
    for r in records:
        h = hashlib.sha256(re.sub(r"\s+", "", r.text).encode()).hexdigest()
        if h not in hashes:
            hashes.add(h)
            out.append(r)
    return out


def source_quota_select(records: list[Rec]) -> list[Rec]:
    by = defaultdict(list)
    for r in records:
        by[r.source].append(r)
    for v in by.values():
        v.sort(key=lambda r: (-r.char_count, r.title))
    desired = {"ruanyifeng": 65_000, "moonlight": 35_000, "xbeta": 25_000}
    selected, chosen = [], set()
    for src, goal in desired.items():
        total = 0
        pool = by.get(src, [])
        topic_counts = Counter()
        # Prefer topic diversity, then length.
        while pool and total < min(goal, sum(x.char_count for x in pool)):
            pool.sort(key=lambda r: (topic_counts[r.topic], -r.char_count))
            r = pool.pop(0)
            selected.append(r); chosen.add(id(r)); total += r.char_count; topic_counts[r.topic] += 1
    current = sum(r.char_count for r in selected)
    remaining = [r for r in records if id(r) not in chosen]
    target = TARGET_TOTAL - current
    if target > 0 and remaining:
        # Rounded subset-sum, 50-character units.
        unit = 50
        tgt = max(0, round(target / unit))
        maxsum = tgt + 150
        dp = {0: None}
        parent = {}
        for i, r in enumerate(remaining):
            w = max(1, round(r.char_count / unit))
            for s in sorted(list(dp.keys()), reverse=True):
                ns = s + w
                if ns <= maxsum and ns not in dp:
                    dp[ns] = i
                    parent[(i, ns)] = s
        best = min(dp, key=lambda s: abs(s - tgt))
        picks = []
        s = best
        while s and dp[s] is not None:
            i = dp[s]
            picks.append(i)
            s = parent[(i, s)]
        selected.extend(remaining[i] for i in reversed(picks))
    # If still low, greedily add shortest articles without overshooting too much.
    current = sum(r.char_count for r in selected)
    for r in sorted((r for r in records if r not in selected), key=lambda r: r.char_count):
        if current >= 216_000:
            break
        selected.append(r); current += r.char_count
    return selected


def partition(records: list[Rec]) -> tuple[list[Rec], list[Rec]]:
    n = len(records)
    best_assign = None
    best_score = float("inf")
    rng = random.Random(2007)
    sources = sorted(set(r.source for r in records))
    for restart in range(60):
        order = list(range(n)); rng.shuffle(order)
        a, b = [], []
        sa = sb = 0
        for i in sorted(order, key=lambda i: records[i].char_count, reverse=True):
            if sa <= sb:
                a.append(i); sa += records[i].char_count
            else:
                b.append(i); sb += records[i].char_count
        assign = [0] * n
        for i in b: assign[i] = 1
        def score(x):
            sums = [0, 0]; sc = [Counter(), Counter()]
            for i, side in enumerate(x):
                sums[side] += records[i].char_count; sc[side][records[i].source] += 1
            val = abs(sums[0] - TARGET_BIN) + abs(sums[1] - TARGET_BIN)
            for src in sources:
                if sum(1 for r in records if r.source == src) >= 2:
                    if sc[0][src] == 0 or sc[1][src] == 0: val += 12_000
                val += abs(sc[0][src] - sc[1][src]) * 150
            return val
        cur = score(assign)
        temp = 2500.0
        for step in range(20_000):
            i = rng.randrange(n)
            assign[i] ^= 1
            nv = score(assign)
            if nv < cur or rng.random() < math.exp((cur - nv) / max(temp, 1)):
                cur = nv
            else:
                assign[i] ^= 1
            temp *= 0.99965
        if cur < best_score:
            best_score, best_assign = cur, assign[:]
    a = [r for i, r in enumerate(records) if best_assign[i] == 0]
    b = [r for i, r in enumerate(records) if best_assign[i] == 1]
    return a, b


def write_outputs(records: list[Rec]) -> None:
    if OUT.exists(): shutil.rmtree(OUT)
    TEXTS.mkdir(parents=True)
    selected = source_quota_select(records)
    total = sum(r.char_count for r in selected)
    if total < 210_000:
        raise RuntimeError(f"Insufficient clean non-policy text: {total} chars from {len(selected)} documents")
    bin1, bin2 = partition(selected)
    for side, items in enumerate([bin1, bin2], 1):
        items.sort(key=lambda r: (r.source, r.title))
        for r in items: r.bin = f"2007_O_{side}"
    allr = bin1 + bin2
    allr.sort(key=lambda r: (r.bin, r.source, r.title))
    name_counts = Counter()
    for idx, r in enumerate(allr, 1):
        base = slug(r.title)
        name_counts[base] += 1
        if name_counts[base] > 1: base += f"_{name_counts[base]}"
        r.text_id = f"2007_O_{idx:03d}"
        r.file_name = f"2007_O_{base}_cleaned.txt"
        (TEXTS / r.file_name).write_text(r.text.strip() + "\n", encoding="utf-8")
    for side, items in enumerate([bin1, bin2], 1):
        body = "\n\n".join(r.text.strip() for r in sorted(items, key=lambda r: r.text_id)) + "\n"
        (OUT / f"2007_O_{side}.txt").write_text(body, encoding="utf-8")
    meta = {
        "counting_rule": "Unicode character count after removing all whitespace; punctuation retained",
        "target_per_bin": TARGET_BIN,
        "bins": {f"2007_O_{i}": {"documents": len(items), "chars": sum(r.char_count for r in items)} for i, items in enumerate([bin1, bin2], 1)},
        "source_totals": {s: {"documents": sum(r.source == s for r in allr), "chars": sum(r.char_count for r in allr if r.source == s)} for s in sorted(set(r.source for r in allr))},
        "records": [asdict(r) | {"text": None} for r in allr],
    }
    (OUT / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    readme = f"""2007_O 非政策类简体中文观点/评论/评测语料包\n\n文档数：{len(allr)}\nBin 1：{meta['bins']['2007_O_1']['chars']} 字符\nBin 2：{meta['bins']['2007_O_2']['chars']} 字符\n总计：{sum(r.char_count for r in allr)} 字符\n\n字符统计：删除所有空白后的 Unicode 字符数，保留标点。\n筛选：首次发表于 2007 年；简体中文；非国家政策、非政府规划、非白皮书、非政策解读。\n类型：软件/互联网评测、科技与媒体评论、书影评论、旅行城市观察、职业学习经验等。\n清洗：删除标题、作者/日期展示、图片与图注、导航、评论区、相关文章、原始标记和脚注；正文措辞不改写，不截断文章。\n\n注意：本包按非商业学术语料研究目的整理。使用者仍应遵守逐篇许可证和署名/相同方式共享要求。\n"""
    (OUT / "README.txt").write_text(readme, encoding="utf-8")
    lic = [
        "来源与许可说明",
        "",
        "1. 善用佳软（xbeta）：作者原创内容采用 CC0 / Public Domain；翻译、转载、投稿不在此列。本包仅纳入作者原创评测/评论。https://xbeta.info/about",
        "2. 月光博客：署名-非商业用途-相同方式共享。https://www.williamlong.info/archives/480.html",
        "3. 阮一峰网络日志：自由转载-非商用-非衍生-保持署名（创意共享3.0）。本包仅作逐字正文抽取，除删除网页元数据/标记外不改写。https://www.ruanyifeng.com/blog/",
        "",
        "逐篇来源：",
    ]
    for r in allr:
        lic.append(f"{r.text_id}\t{r.title}\t{r.author}\t{r.url}\t{r.license_status}\t{r.file_name}")
    (OUT / "LICENSES_AND_SOURCES.txt").write_text("\n".join(lic) + "\n", encoding="utf-8")
    print(json.dumps(meta["bins"], ensure_ascii=False))
    print(json.dumps(meta["source_totals"], ensure_ascii=False))
    print("SELECTED", len(allr), "TOTAL", sum(r.char_count for r in allr))


def main():
    candidates = []
    for func in [collect_ruan, collect_moon, collect_xbeta]:
        try:
            batch = func()
            print("COLLECTED", func.__name__, len(batch), sum(r.char_count for r in batch))
            candidates.extend(batch)
        except Exception as e:
            print("SOURCE_FAILURE", func.__name__, repr(e), file=sys.stderr)
    candidates = dedupe(candidates)
    print("CANDIDATES", len(candidates), sum(r.char_count for r in candidates), Counter(r.source for r in candidates))
    write_outputs(candidates)

if __name__ == "__main__":
    main()
