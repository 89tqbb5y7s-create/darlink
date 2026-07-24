#!/usr/bin/env python3
"""Run v9 sources with the mathematically sufficient 218k pool threshold."""
from __future__ import annotations

import shutil
from pathlib import Path

import build_corpus_2013_v5 as base
import build_corpus_2013_v7 as v7
import build_corpus_2013_v8 as v8
import build_corpus_2013_v9 as v9


def main() -> None:
    shutil.rmtree(base.OUT, ignore_errors=True)
    root = Path("/tmp/corpus2013_sources")
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    ruanyf = root / "read"
    coolshell = root / "haoel"
    gov = root / "gov"
    yihui = root / "yihui"
    govdata = root / "govdata"
    pingmin = root / "pingmin"
    base.clone_at(base.RUANYF_REPO, base.RUANYF_COMMIT, ruanyf)
    base.clone_at(base.COOLSHELL_REPO, base.COOLSHELL_COMMIT, coolshell)
    base.clone_at(base.GOV_REPO, base.GOV_COMMIT, gov)
    base.clone_at(v8.YIHUI_REPO, v8.YIHUI_COMMIT, yihui)
    base.clone_at(v8.GOVDATA_REPO, v8.GOVDATA_COMMIT, govdata)
    base.clone_at(v9.PINGMIN_REPO, v9.PINGMIN_COMMIT, pingmin)
    pool: list[dict] = []
    v7.collect_all_chinese_ruanyf(pool, ruanyf)
    base.collect_coolshell(pool, coolshell)
    base.collect_government(pool, gov)
    v8.collect_yihui(pool, yihui)
    v8.collect_government_dataset(pool, govdata)
    v9.collect_pingmin(pool, pingmin)
    total = sum(item["char_count"] for item in pool)
    print("POOL", len(pool), total, sorted({item["source_platform"] for item in pool}))
    if total < 218_000:
        raise SystemExit(f"insufficient pool for two compliant bins: {total}")
    bins, unused = base.choose_bins(pool)
    print("BIN_RAW", [sum(item["char_count"] for item in selected) for selected in bins])
    base.write_outputs(bins, unused)


if __name__ == "__main__":
    main()
