from __future__ import annotations

import html
import importlib.util
import math
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("base_builder", HERE / "build_2007_nonpolicy_corpus.py")
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)

MOON_OPINION_TITLE = re.compile(
    r"试用|评测|分析|技巧|心得|策略|比较|对比|体验|游记|感想|杂感|推荐|回顾|总结|思考|疑惑|看法|"
    r"培训|最佳|常用|必装|发展前景|安全性|方法|伪命题|如何|为什么|问题|商业模式|开发和营销|"
    r"博客之外|我的|我心中的|不要去|浮夸风|恶搞|真垃圾|有感|观察|历史|选择|生活"
)
MOON_EXCLUDE = re.compile(
    r"翻译|译文|转载|投稿|新闻稿|社会热点大事|政策|条例|通知|政府|国务院|公安|封锁|审查|"
    r"股票|证券|汇率|税收|财政|央行|货币|医疗制度|土地制度|法律制度|判决|入狱|"
    r"发布$|上线$|正式发布$|无法访问$|生日|节日|拜年|节目单|排行榜$"
)


def safe_v2(title: str, text: str, source: str) -> bool:
    n = b.count_chars(text)
    if not text or n < 260 or n > 30_000:
        return False
    if b.FORBIDDEN.search(title + "\n" + text[:3000]):
        return False
    if re.search(r"(?:转载|译文|翻译：|原文作者|新闻稿)", title + text[:500]):
        return False
    if source == "xbeta" and re.search(r"20(?:0[89]|1\d|2\d)年", text):
        return False
    return True


def parse_txtcn_file(path: Path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()
    if len(lines) < 3:
        return None
    title = lines[0].strip().lstrip("➜").strip()
    m = re.search(r"https?://(?:www\.)?williamlong\.info/archives/(\d+)\.html", lines[1])
    if not m:
        return None
    article_id = int(m.group(1))
    url = m.group(0).replace("http://", "https://")
    body_raw = "\n".join(lines[2:])
    soup = BeautifulSoup(body_raw, "lxml")
    for bad in soup.select("script,style,noscript,iframe,figure,figcaption,table,img"):
        bad.decompose()
    text = soup.get_text("\n", strip=True)
    text = re.sub(r"(?m)^\s*Image(?::[^\n]*)?\s*$", "", text)
    text = b.normalize_text(text)
    return title, article_id, url, text


def collect_moon_v2():
    repo = b.ROOT / ".cache" / "txtcn-data"
    if repo.exists():
        shutil.rmtree(repo)
    repo.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
        "https://github.com/txtcn/data.git", str(repo)
    ], check=True)
    subprocess.run(["git", "-C", str(repo), "sparse-checkout", "set", "williamlong.info"], check=True)
    parsed = []
    for p in (repo / "williamlong.info").rglob("*"):
        if p.is_file():
            try:
                item = parse_txtcn_file(p)
                if item:
                    parsed.append(item)
            except Exception as e:
                print("MOON_MIRROR_PARSE_FAIL", p.name, e)
    boundaries = {}
    for title, aid, url, text in parsed:
        if title in {"新年第一篇：新年快乐", "博客2007年度数据统计和排行"}:
            boundaries[title] = aid
    start = boundaries.get("新年第一篇：新年快乐")
    end = boundaries.get("博客2007年度数据统计和排行", 1190)
    if start is None:
        # The archive IDs are chronological; 1190 is independently verified as 2007-12-31.
        # Select the earliest ID among exact January-2007 anchor titles available in the mirror.
        anchors = {"避免Adsense帐号被锁定的技巧", "百度也恶搞？", "电信屏蔽eMule了吗"}
        ids = [aid for title, aid, _, _ in parsed if title in anchors]
        if not ids:
            raise RuntimeError("Could not establish Moonlight Blog 2007 start boundary")
        start = min(ids) - 1
    print("MOON_ID_BOUNDARY", start, end)
    out = []
    for title, aid, url, text in parsed:
        if not (start <= aid <= end):
            continue
        if MOON_EXCLUDE.search(title):
            continue
        # Strongly prefer first-person testing, evaluation, reflection and practical commentary.
        first_person = re.search(r"我|我的|我们|感觉|认为|看来|发现|试用|使用后|建议|经验|心得", text[:1200])
        analytical = MOON_OPINION_TITLE.search(title)
        if not (first_person and analytical):
            continue
        if not safe_v2(title, text, "moonlight"):
            continue
        out.append(b.Rec(
            title, "月光", "moonlight", url,
            "CC BY-NC-SA (署名-非商业用途-相同方式共享)",
            "https://www.williamlong.info/archives/480.html",
            b.topic_of(title, text), text, b.count_chars(text),
            notes=("Official article URL retained; public text mirror used only as technical retrieval fallback because the official site returned HTTP 403 to the automated runner. "
                   "Article ID falls within independently anchored 2007 chronological boundaries. Main prose retained; web metadata, images and navigation removed.")
        ))
    return out


def collect_xbeta_v2():
    out = []
    pairs = list(b.XBETA_DIRECT)
    pairs += [(t, u) for t, u in b.xbeta_index_links().items()]
    used = set()
    for hint, url in pairs:
        if url in used:
            continue
        used.add(url)
        try:
            text = b.html_main(url, hint)
        except Exception as e:
            print("XBETA_FAIL_V2", hint, e)
            continue
        title = hint
        if safe_v2(title, text, "xbeta"):
            out.append(b.Rec(
                title, "善用佳软（张玉新/xbeta）", "xbeta", url,
                "CC0 / Public Domain for xbeta-original content", "https://xbeta.info/about",
                b.topic_of(title, text), text, b.count_chars(text),
                notes=("Official xbeta page; author-original 2007 review/commentary. Excluded if later-year substantive revisions were detected. "
                       "Markup, images, update metadata and navigation removed.")
            ))
        else:
            print("XBETA_EXCLUDED_V2", title, b.count_chars(text))
    return out


def balanced_select(records):
    by = defaultdict(list)
    for r in records:
        by[r.source].append(r)
    for v in by.values():
        v.sort(key=lambda r: (-r.char_count, r.title))
    desired = {"ruanyifeng": 65_000, "moonlight": 65_000, "xbeta": 18_000}
    selected, chosen = [], set()
    for src, goal in desired.items():
        pool = by.get(src, [])[:]
        available = sum(x.char_count for x in pool)
        goal = min(goal, available)
        total = 0
        topics = Counter()
        while pool and total < goal:
            pool.sort(key=lambda r: (topics[r.topic], -r.char_count))
            r = pool.pop(0)
            selected.append(r); chosen.add(id(r)); total += r.char_count; topics[r.topic] += 1
    current = sum(r.char_count for r in selected)
    remaining = [r for r in records if id(r) not in chosen]
    target = b.TARGET_TOTAL - current
    if target > 0:
        unit = 25
        tgt = round(target / unit)
        maxsum = tgt + 300
        reachable = {0: None}
        parent = {}
        for i, r in enumerate(remaining):
            w = max(1, round(r.char_count / unit))
            for s in sorted(list(reachable), reverse=True):
                ns = s + w
                if ns <= maxsum and ns not in reachable:
                    reachable[ns] = i
                    parent[(i, ns)] = s
        best = min(reachable, key=lambda s: abs(s - tgt))
        picks, s = [], best
        while s and reachable[s] is not None:
            i = reachable[s]; picks.append(i); s = parent[(i, s)]
        selected.extend(remaining[i] for i in reversed(picks))
    # Keep the total in an approximate 2 x 110k window.
    total = sum(r.char_count for r in selected)
    if total < 216_000:
        for r in sorted((r for r in records if r not in selected), key=lambda r: r.char_count):
            selected.append(r); total += r.char_count
            if total >= 216_000:
                break
    return selected


def dp_partition(records):
    total = sum(r.char_count for r in records)
    target = total // 2
    unit = 10
    tgt = round(target / unit)
    weights = [max(1, round(r.char_count / unit)) for r in records]
    reachable = {0: None}
    parent = {}
    for i, w in enumerate(weights):
        for s in sorted(list(reachable), reverse=True):
            ns = s + w
            if ns <= tgt + 300 and ns not in reachable:
                reachable[ns] = i
                parent[(i, ns)] = s
    best = min(reachable, key=lambda s: abs(s - tgt))
    picks, s = set(), best
    while s and reachable[s] is not None:
        i = reachable[s]; picks.add(i); s = parent[(i, s)]
    a = [r for i, r in enumerate(records) if i in picks]
    c = [r for i, r in enumerate(records) if i not in picks]
    # Ensure each source with >=2 selected documents appears in both bins.
    sources = {r.source for r in records}
    for src in sources:
        all_src = [r for r in records if r.source == src]
        if len(all_src) < 2:
            continue
        if not any(r.source == src for r in a):
            donor = min((r for r in c if r.source == src), key=lambda r: r.char_count)
            a.append(donor); c.remove(donor)
        if not any(r.source == src for r in c):
            donor = min((r for r in a if r.source == src), key=lambda r: r.char_count)
            c.append(donor); a.remove(donor)
    # Local swaps to tighten length balance while preserving source presence.
    def imbalance(x, y):
        return abs(sum(r.char_count for r in x) - sum(r.char_count for r in y))
    improved = True
    while improved:
        improved = False
        old = imbalance(a, c)
        best_pair = None; best_val = old
        for ra in a:
            for rc in c:
                na = sum(r.char_count for r in a) - ra.char_count + rc.char_count
                nc = total - na
                val = abs(na - nc)
                if val < best_val:
                    best_val = val; best_pair = (ra, rc)
        if best_pair:
            ra, rc = best_pair
            a.remove(ra); c.remove(rc); a.append(rc); c.append(ra); improved = True
    return a, c


b.safe = safe_v2
b.collect_moon = collect_moon_v2
b.collect_xbeta = collect_xbeta_v2
b.source_quota_select = balanced_select
b.partition = dp_partition

if __name__ == "__main__":
    b.main()
