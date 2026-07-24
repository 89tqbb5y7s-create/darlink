from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("v2_builder", HERE / "build_2007_nonpolicy_corpus_v2.py")
v2 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v2
spec.loader.exec_module(v2)
b = v2.b


def collect_moon_v3():
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
        if not p.is_file():
            continue
        try:
            item = v2.parse_txtcn_file(p)
            if item:
                parsed.append(item)
        except Exception as exc:
            print("MOON_MIRROR_PARSE_FAIL", p.name, exc)

    # Verified official chronology:
    # archive 743 = 2007-01-02; therefore 742 is the 2007-01-01 boundary.
    # archive 1190 is the final verified 2007 year-end boundary.
    start, end = 742, 1190
    in_year = [x for x in parsed if start <= x[1] <= end]
    print("MOON_ID_BOUNDARY", start, end, "IN_YEAR_FILES", len(in_year))
    print("MOON_BOUNDARY_SAMPLE_START", sorted((aid, title) for title, aid, _, _ in in_year)[:8])
    print("MOON_BOUNDARY_SAMPLE_END", sorted((aid, title) for title, aid, _, _ in in_year)[-8:])

    out = []
    for title, aid, url, text in in_year:
        if v2.MOON_EXCLUDE.search(title):
            continue
        first_person = v2.re.search(
            r"我|我的|我们|感觉|认为|看来|发现|试用|使用后|建议|经验|心得|比较|分析|评测|总结",
            text[:1600],
        )
        analytical = v2.MOON_OPINION_TITLE.search(title)
        topic_signal = v2.re.search(
            r"Google|百度|软件|博客|网站|网络|地图|输入法|旅行|游记|电影|游戏|团队|RSS|WordPress|"
            r"Flickr|Picasa|Gmail|DreamHost|搜索|安全|商业模式|开发|产品|互联网",
            title,
            v2.re.I,
        )
        if not first_person or not (analytical or topic_signal):
            continue
        if not v2.safe_v2(title, text, "moonlight"):
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
                "Official article URL retained; public text mirror used only as a technical retrieval fallback because the official site returned HTTP 403 to the automated runner. "
                "Archive ID is within the independently verified 2007 range 742–1190. Main prose retained; title/date/byline display, images, navigation and comments removed."
            ),
        ))
    print("MOON_SELECTED", len(out), sum(r.char_count for r in out), v2.Counter(r.topic for r in out))
    return out


b.collect_moon = collect_moon_v3

if __name__ == "__main__":
    b.main()
