#!/usr/bin/env python3
"""Expanded GitHub-snapshot-only 2013 corpus builder."""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from urllib.parse import quote

import build_corpus_2013_v5 as base


EXCLUDE_TITLE = re.compile(
    r"(?:速查|Cheat Sheet|下载地址|壁纸|桌面|插件列表|资源汇总|招聘启事|网站推荐|"
    r"安装记录|配置记录|纯代码|源码下载|命令列表)"
)


def collect_ruanyf_expanded(pool: list[dict], repo: Path) -> None:
    # These are all author-article sections in the fixed mirror. Technical prose is
    # classified as technical review/explainer after code, literal blocks and links are removed.
    include_dirs = {
        "opinions", "essays", "clipboard", "sci-tech", "notes", "business", "books",
        "computer", "developer", "algorithm", "javascript", "internet", "economics",
        "education", "misc", "life", "programmer",
    }
    for path in sorted((repo / "ruanyifeng").rglob("2013*.rst")):
        if path.parent.name not in include_dirs:
            continue
        raw = path.read_text("utf-8", errors="ignore")
        title = base.rst_title(raw, path.stem)
        if EXCLUDE_TITLE.search(title):
            continue
        body = base.clean_rst(raw)
        date_match = re.match(r"(2013)(\d{2})", path.name)
        date = f"2013-{date_match.group(2)}" if date_match else "2013"
        official = base.original_url(raw)
        source = (
            "https://github.com/me115/read/blob/"
            f"{base.RUANYF_COMMIT}/" + quote(str(path.relative_to(repo)), safe="/")
        )
        if path.parent.name in {"computer", "developer", "algorithm", "javascript", "internet", "programmer"}:
            genre = "技术评论 / 方法评述 / 互联网分析"
        elif re.search(r"书|序言|读后感|纪录片|电影", title):
            genre = "书评 / 影评 / 文化评论"
        else:
            genre = "观点 / 社会与科技评论"
        base.add(
            pool,
            title=title,
            author="阮一峰",
            date=date,
            source_url=source,
            official_url=official,
            platform="阮一峰文章固定仓库快照",
            genre=genre,
            rights="CC BY-NC-ND 3.0 (original site-level license)",
            license_url="https://creativecommons.org/licenses/by-nc-nd/3.0/",
            text=body,
            notes=(
                f"Fixed GitHub mirror commit; official_url={official}; original site states "
                "自由转载-非商用-非衍生-保持署名; RST metadata, code/literal blocks, links, "
                "long quotations and back matter removed."
            ),
        )
    print("RUANYF_EXPANDED", len([x for x in pool if x["source_platform"] == "阮一峰文章固定仓库快照"]))


def main() -> None:
    shutil.rmtree(base.OUT, ignore_errors=True)
    root = Path("/tmp/corpus2013_sources")
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    ruanyf = root / "read"
    coolshell = root / "haoel"
    gov = root / "gov"
    base.clone_at(base.RUANYF_REPO, base.RUANYF_COMMIT, ruanyf)
    base.clone_at(base.COOLSHELL_REPO, base.COOLSHELL_COMMIT, coolshell)
    base.clone_at(base.GOV_REPO, base.GOV_COMMIT, gov)
    pool: list[dict] = []
    collect_ruanyf_expanded(pool, ruanyf)
    base.collect_coolshell(pool, coolshell)
    base.collect_government(pool, gov)
    total = sum(x["char_count"] for x in pool)
    print("POOL", len(pool), total, sorted({x["source_platform"] for x in pool}))
    if total < 225_000:
        raise SystemExit(f"insufficient pool: {total}")
    bins, unused = base.choose_bins(pool)
    print("BIN_RAW", [sum(x["char_count"] for x in selected) for selected in bins])
    base.write_outputs(bins, unused)


if __name__ == "__main__":
    main()
