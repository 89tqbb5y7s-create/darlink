from __future__ import annotations

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
spec = importlib.util.spec_from_file_location("v6_builder", HERE / "build_2007_nonpolicy_corpus_v6.py")
v6 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v6
spec.loader.exec_module(v6)
b = v6.b

EXTRA_RUAN_EXCLUDE = re.compile(
    r"面试100题|软件行为准则|图书馆重新开放|告别信|论文的规范|故事|演讲|名言|语录|"
    r"转贴|转帖|转载|译文|翻译|摘录|全文|照片|图片|词典|辨析|语法|介词|"
    r"标点符号|编码笔记|字符编码|RFC|Dublin Core|API$|免费网络资源|新闻奖|"
    r"普利策|统计|数据排行|简历|讣告|去世|猛犸|干尸|面孔2007|病例|癌症|患者|"
    r"煤矿|最脏的城市|工资条|本人成分|传记|拉丁字母|英文字母|术语|定义|"
    r"开幕词|致辞|声明|公告|通知|备忘录|清单|名单|年表|时间表|链接汇总",
    re.I,
)


def collect_ruan_v7():
    repo = b.ROOT / ".cache" / "read"
    if repo.exists():
        shutil.rmtree(repo)
    repo.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/me115/read.git", str(repo)], check=True)
    root = repo / "ruanyifeng"
    out = []
    reasons = Counter()
    for p in sorted(root.rglob("2007*.rst")):
        raw = p.read_text(encoding="utf-8", errors="replace")
        title, url, text = b.clean_rst(raw)
        if not url or "/blog/2007/" not in url:
            reasons["wrong_year"] += 1; continue
        if EXTRA_RUAN_EXCLUDE.search(title):
            reasons["non_opinion_title"] += 1; continue
        n = b.count_chars(text)
        if n < 350 or n > 9_000:
            reasons["length"] += 1; continue
        if v6.v5.STRICT_FORBIDDEN.search(title + "\n" + text[:4000]) or v6.v5.TITLE_BLOCK.search(title):
            reasons["policy_governance"] += 1; continue
        if v6.v5.REPOST_MARKERS.search(raw[:2000]) or v6.v5.REPOST_MARKERS.search(text[:1400]):
            reasons["repost_translation"] += 1; continue
        score = v6.quality_score(title, text)
        strong_title = bool(v6.RUAN_TITLE_INCLUDE.search(title))
        if strong_title and score < 5:
            reasons["weak"] += 1; continue
        if not strong_title and score < 9:
            reasons["weak"] += 1; continue
        # Require at least two explicit evaluative phrases unless title is clearly review/commentary.
        eval_count = len(v6.EVALUATIVE.findall(text[:6000]))
        if eval_count < 2 and not re.search(r"评论|评测|影评|书评|感想|思考|比较|体验|试用|观察|回顾", title):
            reasons["weak"] += 1; continue
        lines = [x for x in text.splitlines() if x.strip()]
        if lines:
            codeish = sum(bool(re.search(r"[{};]|^\s*(?:function|class|var |SELECT |INSERT |<\w+|/\*)", x)) for x in lines)
            if codeish / len(lines) > 0.15:
                reasons["code"] += 1; continue
        quoted = sum(len(x) for x in re.findall(r"[“\"]([^”\"]{20,})[”\"]", text))
        if quoted > len(text) * 0.52:
            reasons["quotation"] += 1; continue
        out.append(b.Rec(
            title=title,
            author="阮一峰",
            source="ruanyifeng",
            url=url,
            license_status="CC BY-NC-ND 3.0; verbatim noncommercial research extract",
            license_url="https://www.ruanyifeng.com/blog/",
            topic=b.topic_of(title, text),
            text=text,
            char_count=n,
            notes=(
                "Public RST mirror used only for technical retrieval; official 2007 article URL retained. "
                "Substantive wording unchanged; RST markup, title/byline display, raw URLs and non-body metadata removed."
            ),
        ))
    print("RUAN_V7_SELECTED", len(out), sum(r.char_count for r in out), Counter(r.topic for r in out))
    print("RUAN_V7_REASONS", reasons)
    for rec in sorted(out, key=lambda r: -r.char_count)[:15]:
        print("RUAN_V7_LONG", rec.char_count, rec.title)
    return out


def collect_appinn_v7():
    discovered = {}
    for month in range(1, 13):
        links = v6.archive_links(month)
        print("APPINN_V7_MONTH", month, len(links))
        discovered.update(links)
    candidates = []
    for url, title in discovered.items():
        if v6.APPINN_TITLE_EXCLUDE.search(title):
            continue
        if not v6.APPINN_TITLE_INCLUDE.search(title):
            continue
        candidates.append((url, title))
    print("APPINN_V7_CANDIDATES", len(candidates))
    out = []
    for idx, (url, hint) in enumerate(candidates, 1):
        try:
            title, author, date_text, text, raw_html = v6.extract_appinn_page(url, hint)
        except Exception as exc:
            print("APPINN_V7_FAIL", url, repr(exc)); continue
        if date_text and "2007" not in date_text:
            continue
        if v6.APPINN_TITLE_EXCLUDE.search(title):
            continue
        raw_text = BeautifulSoup(raw_html, "lxml").get_text("\n", strip=True)
        if re.search(r"\[译文\]|译者声明|原文链接|中文翻译|转载请保留此声明|本文转载|绿色汉化|破解版", title + raw_text[:1800]):
            continue
        n = b.count_chars(text)
        if n < 300 or n > 6_500:
            continue
        if v6.v5.STRICT_FORBIDDEN.search(title + "\n" + text[:3000]) or v6.v5.TITLE_BLOCK.search(title):
            continue
        if len(v6.EVALUATIVE.findall(text[:5000])) < 1 and not re.search(r"我|个人|觉得|发现|推荐|缺点|优点|相比|试用|使用", text[:1800]):
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
            char_count=n,
            notes=(
                "Official 2007 Appinn article page. A limited topic-diverse sample was selected rather than reproducing the complete archive. "
                "Title/date/byline display, images, captions, download blocks, navigation, comments and related links removed."
            ),
        ))
        if idx % 40 == 0:
            print("APPINN_V7_PROGRESS", idx, len(out), sum(r.char_count for r in out))
        time.sleep(0.25)
    # Retain a broad but incomplete sample; prioritize topic diversity and evaluative strength.
    selected = []
    topics = Counter()
    chars = 0
    while out and len(selected) < 95 and chars < 100_000:
        out.sort(key=lambda r: (topics[r.topic], -v6.quality_score(r.title, r.text), -r.char_count))
        rec = out.pop(0)
        selected.append(rec); topics[rec.topic] += 1; chars += rec.char_count
    print("APPINN_V7_SELECTED", len(selected), chars, topics)
    return selected


def select_v7(records):
    by = defaultdict(list)
    for rec in records:
        by[rec.source].append(rec)
    for vals in by.values():
        vals.sort(key=lambda r: (-v6.quality_score(r.title, r.text), -r.char_count))
    goals = {"ruanyifeng": 115_000, "appinn": 91_000, "xbeta": 14_000}
    selected, chosen = [], set()
    for source, goal in goals.items():
        pool = by.get(source, [])[:]
        total = 0
        topics = Counter()
        while pool and total < goal:
            pool.sort(key=lambda r: (topics[r.topic], -v6.quality_score(r.title, r.text), -r.char_count))
            rec = pool.pop(0)
            selected.append(rec); chosen.add(id(rec)); total += rec.char_count; topics[rec.topic] += 1
        print("SOURCE_SELECTION", source, len([r for r in selected if r.source == source]), total)
    current = sum(r.char_count for r in selected)
    remaining = [r for r in records if id(r) not in chosen]
    target = b.TARGET_TOTAL - current
    if remaining:
        unit = 10
        tgt = round(abs(target) / unit)
        if target > 0:
            maxsum = tgt + 300
            reachable = {0: None}; parent = {}
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
    # Fine-tune by removing low-scoring records only when it improves distance and remains above 215k.
    changed = True
    while changed:
        changed = False
        for rec in sorted(selected, key=lambda r: (v6.quality_score(r.title, r.text), r.char_count)):
            nt = total - rec.char_count
            if nt >= 215_000 and abs(nt - b.TARGET_TOTAL) < abs(total - b.TARGET_TOTAL):
                selected.remove(rec); total = nt; changed = True; break
    print("V7_FINAL_SELECTION", len(selected), total, Counter(r.source for r in selected), Counter(r.topic for r in selected))
    return selected


b.collect_ruan = collect_ruan_v7
b.collect_moon = collect_appinn_v7
b.collect_xbeta = v6.collect_xbeta_quality
b.source_quota_select = select_v7
b.partition = v6.partition_balanced

if __name__ == "__main__":
    b.main()
