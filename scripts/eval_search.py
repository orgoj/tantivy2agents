#!/usr/bin/env python3
"""Compare search modes on a query set: rank of the expected file and latency.

Usage: mise run eval-search -- <project dir> <queries.json> [mode ...]

queries.json is a list of {"query": "...", "expect": "path substring"}.
Modes default to bm25 and hybrid. The CLI runs in the project directory the
way an agent calls it, so latency includes process start.
"""

import json
import os
import shutil
import subprocess
import sys
import time

LIMIT = 10


def run(project, query, mode):
    cli = shutil.which("tantivy2agents", path=os.path.dirname(sys.executable))
    started = time.perf_counter()
    proc = subprocess.run(
        [cli or "tantivy2agents", "search", query, "-f", "json", "-l", str(LIMIT)]
        + ["--mode", mode, "-q"],
        cwd=project,
        capture_output=True,
        text=True,
    )
    elapsed = time.perf_counter() - started
    if proc.returncode != 0:
        return None, elapsed, proc.stderr.strip().splitlines()[-1:]
    if proc.stdout.startswith("No results"):
        return [], elapsed, []
    paths = [r["path"] for r in json.loads(proc.stdout)["results"]]
    warnings = [line for line in proc.stderr.splitlines() if "WARNING" in line]
    return paths, elapsed, warnings


def rank_of(paths, expect):
    for rank, path in enumerate(paths or [], start=1):
        if expect in path:
            return rank
    return None


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    project, queries_file = sys.argv[1], sys.argv[2]
    modes = sys.argv[3:] or ["bm25", "hybrid"]
    with open(queries_file, encoding="utf-8") as f:
        queries = json.load(f)

    totals = {m: {"hit5": 0, "rr": 0.0, "time": []} for m in modes}
    failures = []
    print(" | ".join([f"{m:>8}" for m in modes] + ["query"]))
    for item in queries:
        cells = []
        for mode in modes:
            paths, elapsed, warnings = run(project, item["query"], mode)
            if paths is None:
                failures.append(f"{mode} {item['query']!r}: {' '.join(warnings)}")
                cells.append(f"{'E':>8}")
                continue
            rank = rank_of(paths, item["expect"])
            t = totals[mode]
            t["time"].append(elapsed)
            if rank:
                t["rr"] += 1.0 / rank
                t["hit5"] += rank <= 5
            mark = "!" if warnings else ""
            cells.append(f"{(str(rank) if rank else '-') + mark:>8}")
        print(" | ".join(cells + [item["query"]]))

    print()
    n = len(queries)
    for mode in modes:
        t = totals[mode]
        times = sorted(t["time"])
        print(
            f"{mode:>8}: hit@5 {t['hit5']}/{n}  MRR@{LIMIT} {t['rr'] / n:.2f}  "
            f"median {times[len(times) // 2]:.2f} s  max {times[-1]:.2f} s"
        )
    print("rank '-' = not in top", LIMIT, "; '!' = warning on stderr; E = CLI error")
    if failures:
        print("\nCLI errors (figures above are not valid):")
        for failure in failures:
            print(" ", failure)
        sys.exit(1)


if __name__ == "__main__":
    main()
