"""Retrieval benchmark runner.

Usage: python3 tests/_run_benchmark.py

Measures Top1, Top3, Top5, MRR against ground-truth expected sections.
Runs queries through the live retrieval pipeline (no HTTP overhead).
"""

import json
import os
import sys
import time
from pathlib import Path

# The app's code expects /app as cwd for imports and dataset paths
os.chdir("/app")
sys.path.insert(0, "/app")

from database import SessionLocal
from search import analyze_description


def load_benchmark(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_benchmark(benchmark: list[dict]) -> dict:
    db = SessionLocal()
    total = len(benchmark)
    top1_correct = 0
    top3_correct = 0
    top5_correct = 0
    reciprocal_ranks: list[float] = []
    errors = 0
    details = []

    for i, item in enumerate(benchmark):
        query = item["query"]
        expected = set(item["expected_sections"])
        topic = item.get("topic", "?")

        try:
            result = analyze_description(query, db)
        except Exception as e:
            print(f"  ERROR [{i+1}/{total}]: {e}")
            errors += 1
            details.append({"query": query, "error": str(e), "expected": list(expected)})
            continue

        # Build ranked list of sections from the response
        ranked = []
        primary_sec = result.get("section")
        if primary_sec:
            ranked.append(primary_sec)
        for rule in (result.get("related_rules") or []):
            sec = rule.get("section")
            if sec and sec not in ranked:
                ranked.append(sec)
        for bylaw in (result.get("related_bylaws") or []):
            sec = bylaw.get("section")
            if sec and sec not in ranked:
                ranked.append(sec)

        found_expected = [s for s in expected if s in ranked]
        matched = bool(found_expected)

        # Top1
        if ranked and ranked[0] in expected:
            top1_correct += 1

        # Top3
        if any(s in expected for s in ranked[:3]):
            top3_correct += 1

        # Top5
        if any(s in expected for s in ranked[:5]):
            top5_correct += 1

        # MRR
        rr = 0.0
        for rank, sec in enumerate(ranked, start=1):
            if sec in expected:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)

        details.append({
            "query": query,
            "topic": topic,
            "expected": list(expected),
            "ranked": ranked,
            "matched": matched,
            "top1": ranked[0] if ranked else None,
            "reciprocal_rank": rr,
        })

        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{total}")

    db.close()

    mrr = sum(reciprocal_ranks) / max(len(reciprocal_ranks), 1)
    return {
        "total": total,
        "top1": top1_correct,
        "top3": top3_correct,
        "top5": top5_correct,
        "mrr": round(mrr, 4),
        "errors": errors,
        "top1_pct": round(top1_correct / total * 100, 1),
        "top3_pct": round(top3_correct / total * 100, 1),
        "top5_pct": round(top5_correct / total * 100, 1),
        "details": details,
    }


def print_report(stats: dict) -> None:
    print()
    print("=" * 50)
    print("RETRIEVAL BENCHMARK RESULTS")
    print("=" * 50)
    print(f"  Total queries:  {stats['total']}")
    print(f"  Errors:         {stats['errors']}")
    print(f"  Top-1 accuracy: {stats['top1']}/{stats['total']} ({stats['top1_pct']}%)")
    print(f"  Top-3 accuracy: {stats['top3']}/{stats['total']} ({stats['top3_pct']}%)")
    print(f"  Top-5 accuracy: {stats['top5']}/{stats['total']} ({stats['top5_pct']}%)")
    print(f"  MRR:            {stats['mrr']}")
    print()

    # Per-topic breakdown
    from collections import defaultdict
    topic_stats: dict[str, dict] = defaultdict(lambda: {"total": 0, "top1": 0, "top3": 0, "top5": 0, "rrs": []})
    for d in stats["details"]:
        t = d["topic"]
        topic_stats[t]["total"] += 1
        ranked = d["ranked"]
        expected = d["expected"]
        if ranked and ranked[0] in expected:
            topic_stats[t]["top1"] += 1
        if any(s in expected for s in ranked[:3]):
            topic_stats[t]["top3"] += 1
        if any(s in expected for s in ranked[:5]):
            topic_stats[t]["top5"] += 1
        topic_stats[t]["rrs"].append(d["reciprocal_rank"])

    print("Per-Topic Breakdown:")
    print(f"  {'Topic':<20} {'Total':<6} {'Top1':<6} {'Top3':<6} {'Top5':<6} {'MRR':<8}")
    print("  " + "-" * 55)
    for topic in sorted(topic_stats.keys()):
        ts = topic_stats[topic]
        mrr_t = round(sum(ts["rrs"]) / max(len(ts["rrs"]), 1), 4)
        print(f"  {topic:<20} {ts['total']:<6} {ts['top1']:<6} {ts['top3']:<6} {ts['top5']:<6} {mrr_t:<8}")

    # Per-query details
    print()
    print("Per-Query Mismatches (expected not in ranked top-5):")
    print()
    for d in stats["details"]:
        expected = d["expected"]
        ranked = d["ranked"]
        matched_any = any(s in ranked[:5] for s in expected)
        if not matched_any and ranked:
            print(f"  MISS: {d['topic']:15s} | expected={expected} | top5={ranked[:5]}")
            print(f"        query: {d['query'][:80]}")
            print()


if __name__ == "__main__":
    bench_path = os.environ.get(
        "BENCHMARK_PATH",
        "/app/tests/retrieval_benchmark.json",
    )
    print(f"Loading benchmark from: {bench_path}")
    benchmark = load_benchmark(bench_path)
    print(f"Loaded {len(benchmark)} queries")
    print()
    stats = run_benchmark(benchmark)
    print_report(stats)
