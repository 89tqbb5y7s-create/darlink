import re
import json
import hashlib
import zipfile
import shutil
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag
import trafilatura

TARGET = 110_000
OUT = Path("2008_O_payload")
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
TXT = OUT / "texts"
TXT.mkdir()

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 corpus-research/1.0"})

POLICY_WORDS = [
    "国家政策", "政府政策", "法规解读", "施政", "国务院", "中央政府",
    "公共政策", "政治制度", "选举制度", "政党", "外交政策", "监管政策",
    "政府工作报告", "行政法规", "政府施政"
]


def nonspace_count(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def norm_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    text = re.sub(r"\[(?:\d+|注\d+|[一二三四五六七八九十]+)\]", "", text)
    text = re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩]", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def policy_ok(title: str, text: str) -> bool:
    probe = title + "\n" + text[:7000]
    return not any(word in probe for word in POLICY_WORDS)


def cut_footer(text: str) -> str:
    markers = [
        "\n原文地址：", "\n原文地址:", "\n作者：", "\n作者:", "\n编辑：", "\n编辑:",
        "\n相关文章", "\n相关链接", "\n延伸阅读", "\n参考资料", "\n参考文献",
        "\n网友评论", "\n评论列表", "\n我要评论", "\nComments", "\n评论："
    ]
    cuts = []
    for marker in markers:
        pos = text.find(marker)
        if pos > 700:
            cuts.append(pos)
    if cuts:
        text = text[:min(cuts)]
    return text


def clean_rst(raw: str):
    lines = raw.replace("\r", "").split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and lines[0].lstrip().startswith(".. _"):
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    title = lines.pop(0).strip() if lines else ""
    if lines and re.fullmatch(r"[=\-~^`:#*+]{3,}", lines[0].strip()):
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and ("mindhacks.cn" in lines[0] or re.match(r"`[^`]+ <https?://", lines[0].strip())):
        lines.pop(0)

    out = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(".. note::"):
            break
        if stripped.startswith((".. image::", ".. figure::", ".. |", ".. _")):
            continue
        if re.fullmatch(r"[=\-~^`:#*+]{3,}", stripped):
            continue
        line = re.sub(r"`([^`<]+?)\s*<https?://[^>]+>`__?", r"\1", line)
        line = re.sub(r"`([^`]+?)`__?", r"\1", line)
        line = line.replace("**", "").replace("\\", "")
        line = re.sub(r"^\s*#\.\s*", "", line)
        line = re.sub(r"^\s*\|\s?", "", line)
        line = re.sub(r"\|[A-Za-z0-9_\-]+\|", "", line)
        line = re.sub(r"\[(?:\d+|注\d+)\]", "", line)
        out.append(line.rstrip())

    text = cut_footer("\n".join(out))
    text = norm_text(text)
    if title and text.startswith(title):
        text = text[len(title):].lstrip("\n ")
    return title, text


def html_main(url: str, title_hint: str = "") -> str:
    response = S.get(url, timeout=45)
    response.raise_for_status()
    text = trafilatura.extract(
        response.text,
        include_comments=False,
        include_tables=False,
        include_links=False,
        include_images=False,
        favor_precision=True,
        output_format="txt",
    ) or ""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        if title_hint and stripped == title_hint.strip():
            continue
        if re.search(r"^(作者|日期|发布时间|来源|本文链接|永久链接|标签|分类)[:：]", stripped):
            continue
        if stripped.startswith("Image:"):
            continue
        lines.append(line)
    return norm_text(cut_footer("\n".join(lines)))


def add_doc(docs, source, title, author, url, text, license_status, topic, note):
    text = norm_text(text)
    if not text or nonspace_count(text) < 700:
        return
    if not policy_ok(title, text):
        return
    digest = hashlib.sha256(re.sub(r"\s+", "", text).encode("utf-8")).hexdigest()
    if any(item["hash"] == digest for item in docs):
        return
    docs.append({
        "source": source,
        "title": title,
        "author": author,
        "url": url,
        "text": text,
        "char_count": nonspace_count(text),
        "license": license_status,
        "topic": topic,
        "note": note,
        "hash": digest,
    })


docs = []

# MindHacks: source files retain the original article URL and author metadata.
mind_files = [
    "200804_reading-method.rst",
    "200806_how-memory-works.rst",
    "200807_learning-habits-part1.rst",
    "200807_learning-habits-part2.rst",
    "200809_learning-habits-part3.rst",
    "200812_learning-habits-part4.rst",
    "200812_how-to-think-straight.rst",
    "200810_methodology-for-programmers.rst",
    "200806_why-is-quicksort-so-quick.rst",
    "200807_the-importance-of-knowing-why.rst",
    "200804_learning-from-polya.rst",
    "200809_the-magical-bayesian-method.rst",
    "200809_machine-learning-and-ai-resources.rst",
]

for filename in mind_files:
    raw_url = f"https://raw.githubusercontent.com/me115/read/master/pongba/allpapers/{filename}"
    response = S.get(raw_url, timeout=45)
    if response.status_code != 200:
        print("MINDHACKS_FETCH_FAIL", filename, response.status_code)
        continue
    response.encoding = "utf-8"
    title, text = clean_rst(response.text)
    match = re.search(r"原文地址[:：]\s*(https?://\S+)", response.text)
    original_url = match.group(1).rstrip() if match else raw_url
    topic = "学习与认知评论"
    if any(key in title for key in ["贝叶斯", "快排", "算法", "波利亚"]):
        topic = "数学与算法评论"
    elif "程序员" in title:
        topic = "程序设计方法评论"
    elif "人工智能" in title or "机器学习" in title:
        topic = "人工智能学习评论"
    add_doc(
        docs, "MindHacks", title, "刘未鹏", original_url, text,
        "作者明确允许转载；须注明作者、出处和原始链接", topic,
        "原始博客正文；GitHub文本镜像仅用于技术恢复；已删除标题、作者/编辑信息、原始链接行、参考资料及数字角标。"
    )

# 善用佳软: original long-form software and Internet commentary.
xbeta_items = [
    ("如何选择软件：深度用户与浅层用户的区别", "https://xbeta.info/software-choice.htm", "软件选择评论"),
    ("善用佳软博客原则：友情链接", "https://xbeta.info/policy-links.htm", "博客文化评论"),
    ("Gmail Labs 新功能不完全手册 v1.4", "https://xbeta.info/gmail-labs.htm", "互联网产品评测"),
]
for title, url, topic in xbeta_items:
    try:
        text = html_main(url, title)
        for marker in ["更新历史", "版本历史", "条评论", "发表评论"]:
            pos = text.find("\n" + marker)
            if pos > 800:
                text = text[:pos]
        add_doc(
            docs, "善用佳软", title, "张玉新（xbeta）", url, text,
            "CC BY-NC-SA 2.5（网站早期声明）；作者后续声明原创内容进入公共领域", topic,
            "原生数字文本；已删除标题、页面导航、相关文章、评论区和非正文元数据。"
        )
    except Exception as exc:
        print("XBETA_FAIL", url, repr(exc))

# 月光博客: selected non-policy review/commentary posts from complete 2008 archives.
william_targets = {
    "百度安全中心评测": "互联网安全产品评测",
    "常用的Web 2.0服务和网站": "互联网服务评论",
    "常用的 Web 2.0 服务和网站": "互联网服务评论",
    "我是怎么消灭Google Reader 1000+的": "数字阅读经验评论",
    "我是怎么消灭 Google Reader 1000+": "数字阅读经验评论",
    "Google Reader的订阅人数统计": "网络产品观察",
    "Google Reader订阅人数统计": "网络产品观察",
    "DreamHost主机故障分析": "网络服务评论",
}

for archive_url in ["https://info.williamlong.info/2008/01/", "https://info.williamlong.info/2008/02/"]:
    try:
        response = S.get(archive_url, timeout=45)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        for heading in soup.find_all("h3"):
            link = heading.find("a")
            if not link:
                continue
            title = " ".join(link.get_text(" ", strip=True).split())
            normalized_title = re.sub(r"\s+", "", title)
            matched = None
            for candidate_title, topic in william_targets.items():
                if re.sub(r"\s+", "", candidate_title) == normalized_title:
                    matched = (candidate_title, topic)
                    break
            if not matched:
                continue
            parts = []
            for sibling in heading.next_siblings:
                if isinstance(sibling, Tag) and sibling.name in ("h2", "h3"):
                    break
                if isinstance(sibling, Tag):
                    for bad in sibling.select("script,style,noscript,img,figure,figcaption"):
                        bad.decompose()
                    segment = sibling.get_text("\n", strip=True)
                    if segment:
                        parts.append(segment)
            text = norm_text("\n\n".join(parts))
            source_url = urljoin(archive_url, link.get("href", ""))
            add_doc(
                docs, "月光博客", title, "William Long", source_url, text,
                "CC BY-NC-SA 2.5（网站版权声明）", matched[1],
                "从作者2008年月度存档的完整正文提取；已删除标题、图片/图注、页面导航和非正文元数据。"
            )
    except Exception as exc:
        print("WILLIAM_FAIL", archive_url, repr(exc))

print("CANDIDATES_BEGIN")
for index, item in enumerate(docs):
    print(index, item["source"], item["char_count"], item["title"])
print("CANDIDATES_END")

# Drop suspiciously long extractions that likely contain page chrome/comments.
docs = [
    item for item in docs
    if item["char_count"] <= 45_000
    and not any(word in item["title"] for word in ["国家政策", "政府政策", "法规解读"])
]

# Require source diversity, then select complete articles closest to 110,000 characters.
mandatory = []
for source, minimum in [("善用佳软", 2), ("月光博客", 2)]:
    pool = sorted(
        [i for i, item in enumerate(docs) if item["source"] == source],
        key=lambda i: docs[i]["char_count"],
        reverse=True,
    )
    mandatory.extend(pool[:min(minimum, len(pool))])
mandatory = sorted(set(mandatory))
remaining = [i for i in range(len(docs)) if i not in mandatory]

best = None
for mask in range(1 << len(remaining)):
    indices = mandatory.copy()
    for bit, index in enumerate(remaining):
        if mask >> bit & 1:
            indices.append(index)
    sources = {docs[i]["source"] for i in indices}
    mind_count = sum(docs[i]["source"] == "MindHacks" for i in indices)
    if len(sources) < 3 or mind_count < 4 or len(indices) < 9:
        continue
    total = sum(docs[i]["char_count"] for i in indices)
    band_penalty = 0 if 106_000 <= total <= 114_000 else min(abs(total - 106_000), abs(total - 114_000)) * 5
    score = band_penalty + abs(total - TARGET) - len(indices) * 10
    if best is None or score < best[0]:
        best = (score, total, indices)

if best is None:
    indices = list(range(len(docs)))
    best = (abs(sum(item["char_count"] for item in docs) - TARGET), sum(item["char_count"] for item in docs), indices)

_, _, selected_indices = best
selected = [docs[i] for i in sorted(selected_indices)]
source_order = {"善用佳软": 0, "月光博客": 1, "MindHacks": 2}
selected.sort(key=lambda item: (source_order.get(item["source"], 9), item["title"]))

manifest = []
for number, item in enumerate(selected, 1):
    slug = re.sub(r"[^a-z0-9]+", "_", item["url"].lower().split("/")[-1].split(".")[0]).strip("_") or f"text{number:03d}"
    filename = f"2008_O_{number:03d}_{slug[:45]}_cleaned.txt"
    (TXT / filename).write_text(item["text"] + "\n", encoding="utf-8")
    manifest.append({
        "#": number,
        "text_id": f"2008_O_{number:03d}",
        "bin": "2008_O_bin01",
        "first_publication_year": 2008,
        "title": item["title"],
        "author": item["author"],
        "source_url_or_identifier": item["url"],
        "simplified or traditional Chinese": "simplified Chinese",
        "char_count": item["char_count"],
        "ocr_quality": "high (native digital; cleaned)",
        "copyright_status": item["license"],
        "notes": f"{item['topic']}；{item['note']}；不含国家政策类评论。",
        "filename": filename,
        "source_name": item["source"],
    })

combined = "\n\n".join(item["text"] for item in selected).strip() + "\n"
(OUT / "2008_O_bin01_combined.txt").write_text(combined, encoding="utf-8")
actual = nonspace_count(combined)

manifest_payload = {
    "target_characters": TARGET,
    "actual_characters": actual,
    "document_count": len(manifest),
    "sources": sorted({record["source_name"] for record in manifest}),
    "records": manifest,
}
(OUT / "manifest.json").write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")

(OUT / "SOURCE_LICENSES.txt").write_text(
    "2008_O 来源与许可说明\n\n"
    "1. MindHacks（刘未鹏）：文章原页明确允许转载，条件为注明作者、出处和原始链接。本包在 Excel/manifest 中逐篇保留作者与原始链接。\n"
    "2. 善用佳软（xbeta/张玉新）：网站早期采用 CC BY-NC-SA 2.5；作者后续声明其原创内容进入公共领域。\n"
    "3. 月光博客（William Long）：网站版权页声明使用 CC BY-NC-SA 2.5。\n\n"
    "清洗范围：仅正文；删除标题、作者/日期等页面元数据、摘要/关键词（如有）、图表及图注、参考资料/参考文献、评论区、相关链接、页眉页脚、[1] 等数字引用角标。\n"
    "题材排除：国家政策、政府施政、法规解读、政治制度及其他政策类评论。\n",
    encoding="utf-8",
)

zip_path = Path("2008_O_payload.zip")
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in OUT.rglob("*"):
        if path.is_file():
            archive.write(path, path.relative_to(OUT.parent))

print("RESULT_ACTUAL", actual)
print("RESULT_DOCS", len(manifest))
print("RESULT_SOURCES", sorted({record["source_name"] for record in manifest}))
print("RESULT_ZIP", zip_path.resolve())
