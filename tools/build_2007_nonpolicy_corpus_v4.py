from __future__ import annotations

import importlib.util
import re
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("v2_builder", HERE / "build_2007_nonpolicy_corpus_v2.py")
v2 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v2
spec.loader.exec_module(v2)
b = v2.b

JINA_PREFIX = "https://r.jina.ai/https://"
TITLE_INCLUDE = re.compile(
    r"Google|百度|雅虎|微软|网站|博客|网络|互联网|搜索|地图|Earth|Gmail|Flickr|Picasa|RSS|"
    r"Feed|软件|输入法|浏览器|WordPress|Z-Blog|DreamHost|服务器|域名|安全|网银|eMule|"
    r"游戏|电影|旅行|游记|凤凰|张家界|深圳|团队|培训|生活|经验|技巧|评测|试用|比较|"
    r"分析|策略|模式|思考|感想|有感|回顾|总结|推荐|疑惑|问题|发展|开发|营销|产品|"
    r"博客之外|我的|我心中的|不要去|浮夸风|恶搞|真垃圾|历史|选择|管理|应用|功能",
    re.I,
)
TITLE_EXCLUDE = re.compile(
    r"政策|条例|通知|政府|国务院|公安|法院|判决|法律|制度|股票|证券|基金|汇率|税收|"
    r"财政|央行|货币|房价|房地产|医疗|外交|入狱|被捕|封锁|审查|共产党|政治|"
    r"翻译|译文|投稿|新闻稿|正式发布|发布会邀请|招聘|节日|生日|节目单|排行榜$|"
    r"下载$|源码$|代码$|补丁$|升级$|更新$|版本发布$|服务中断$|无法访问$",
    re.I,
)


def jina_get(target_url: str, attempts: int = 4) -> str:
    parsed = urlparse(target_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(target_url)
    normalized = target_url.replace("http://", "https://", 1)
    reader_url = JINA_PREFIX + normalized.removeprefix("https://")
    last = None
    for attempt in range(attempts):
        try:
            r = b.S.get(
                reader_url,
                timeout=120,
                headers={
                    "Accept": "text/plain",
                    "X-Return-Format": "markdown",
                    "X-With-Generated-Alt": "false",
                },
            )
            if r.status_code == 200 and len(r.text) > 200:
                return r.text
            last = RuntimeError(f"HTTP {r.status_code}: {reader_url}")
        except Exception as exc:
            last = exc
        time.sleep(3 + attempt * 3)
    raise RuntimeError(str(last))


def discover_moon_urls():
    discovered = {}
    for month in range(1, 13):
        archive = f"https://www.williamlong.info/date/2007-{month:02d}.html"
        try:
            raw = jina_get(archive)
        except Exception as exc:
            print("MOON_JINA_ARCHIVE_FAIL", archive, repr(exc))
            continue
        print("MOON_ARCHIVE_BYTES", month, len(raw))
        # Most Reader output uses Markdown links.
        for title, url in re.findall(
            r"\[([^\]\n]{2,180})\]\((https?://(?:www\.)?williamlong\.info/archives/\d+\.html)\)",
            raw,
            flags=re.I,
        ):
            title = b.normalize_text(title).replace("\n", " ").strip()
            discovered.setdefault(url.replace("http://", "https://"), title)
        # Fallback for headings followed by a URL elsewhere in the same block.
        blocks = re.split(r"(?m)(?=^#{1,3}\s+)", raw)
        for block in blocks:
            um = re.search(r"https?://(?:www\.)?williamlong\.info/archives/\d+\.html", block, re.I)
            hm = re.match(r"(?m)^#{1,3}\s+(.+?)\s*$", block)
            if um and hm:
                title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", hm.group(1)).strip()
                discovered.setdefault(um.group(0).replace("http://", "https://"), title)
        time.sleep(1.0)
    print("MOON_DISCOVERED", len(discovered))
    return discovered


def clean_jina_article(raw: str, title_hint: str):
    title = title_hint
    tm = re.search(r"(?m)^Title:\s*(.+?)\s*$", raw)
    if tm:
        title = tm.group(1).strip()
    date_m = re.search(r"(?m)(?:Published Time:|发布日期[:：]?|发布时间[:：]?)\s*([^\n]+)", raw)
    body = raw.split("Markdown Content:", 1)[-1]
    lines = body.splitlines()
    cleaned = []
    skipped_title = False
    for line in lines:
        line = line.strip()
        if not line:
            cleaned.append("")
            continue
        if re.match(r"^#{1,6}\s+", line):
            h = re.sub(r"^#{1,6}\s+", "", line).strip()
            h = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", h)
            if not skipped_title and b.norm_title(h) == b.norm_title(title):
                skipped_title = True
                continue
            line = h
        if re.search(r"^(?:2007[-年/.]|作者[:：]|分类[:：]|评论[:：]|浏览[:：]|URL Source:|Published Time:)", line):
            continue
        if re.search(r"^(?:上一篇|下一篇|相关文章|相关阅读|发表评论|评论列表|标签[:：]|分享到|月光博客网站地图|订阅本站)", line):
            break
        if re.match(r"^!\[", line) or line.startswith("Image:"):
            continue
        line = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        line = re.sub(r"<https?://[^>]+>", "", line)
        line = re.sub(r"https?://\S+", "", line)
        line = line.replace("**", "").replace("__", "").replace("`", "")
        cleaned.append(line)
    text = b.normalize_text("\n".join(cleaned))
    # Remove duplicated leading title/metadata produced by some pages.
    lead = text.splitlines()
    while lead and (
        b.norm_title(lead[0]) == b.norm_title(title)
        or re.search(r"^(?:月光博客|2007[-年/.]|作者[:：]|分类[:：]|评论[:：]|浏览[:：])", lead[0])
    ):
        lead.pop(0)
    text = b.normalize_text("\n".join(lead))
    return title, (date_m.group(1).strip() if date_m else ""), text


def collect_moon_v4():
    discovered = discover_moon_urls()
    candidates = []
    for url, title in discovered.items():
        if TITLE_EXCLUDE.search(title):
            continue
        if not TITLE_INCLUDE.search(title):
            continue
        candidates.append((url, title))
    candidates.sort(key=lambda x: int(re.search(r"/(\d+)\.html", x[0]).group(1)))
    print("MOON_TITLE_CANDIDATES", len(candidates))

    out = []
    for idx, (url, title_hint) in enumerate(candidates, 1):
        try:
            raw = jina_get(url)
            title, date_text, text = clean_jina_article(raw, title_hint)
        except Exception as exc:
            print("MOON_JINA_ARTICLE_FAIL", url, repr(exc))
            time.sleep(3.2)
            continue
        if date_text and "2007" not in date_text:
            print("MOON_WRONG_DATE", title, date_text)
            time.sleep(3.2)
            continue
        # Exclude translated/submitted content using page metadata and body signals.
        header = raw[:1800]
        if re.search(r"作者[:：]\s*(?:翻译|投稿|转载)|作者[:：].{0,20}(?:翻译|投稿)", header):
            time.sleep(3.2)
            continue
        if re.search(r"(?:作者：|原文作者|英文原文|翻译：|译者：)", text[:800]):
            time.sleep(3.2)
            continue
        first_person = re.search(
            r"我|我的|我们|感觉|认为|看来|发现|试用|使用后|建议|经验|心得|比较|分析|评测|总结",
            text[:1800],
        )
        if not first_person:
            time.sleep(3.2)
            continue
        if not v2.safe_v2(title, text, "moonlight"):
            print("MOON_EXCLUDED_BODY", title, b.count_chars(text))
            time.sleep(3.2)
            continue
        out.append(b.Rec(
            title=title,
            author="月光",
            source="moonlight",
            url=url,
            license_status="CC BY-NC-SA (署名-非商业用途-相同方式共享)",
            license_url="https://www.williamlong.info/archives/480.html",
            topic=b.topic_of(title, text),
            text=text,
            char_count=b.count_chars(text),
            notes=(
                "Official 2007 article URL and date archive retained. Jina Reader was used only as a technical rendering layer after the official site returned HTTP 403 to the automated runner. "
                "Main prose retained; title/date/byline display, images, navigation, comments and related links removed."
            ),
        ))
        if idx % 20 == 0:
            print("MOON_PROGRESS", idx, len(out), sum(r.char_count for r in out))
        time.sleep(3.2)
    print("MOON_SELECTED", len(out), sum(r.char_count for r in out), Counter(r.topic for r in out))
    return out


b.collect_moon = collect_moon_v4

if __name__ == "__main__":
    b.main()
