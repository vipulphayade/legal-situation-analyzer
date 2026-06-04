"""Reranker benchmark: compares heuristic scoring vs cross-encoder reranking.

Runs the current pipeline to score all candidates, takes top-20, then
optionally reranks with a cross-encoder and measures the delta.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict

os.chdir("/app")
sys.path.insert(0, "/app")

from database import SessionLocal
from search import (
    fetch_all_candidates,
    score_candidate,
    extract_keywords,
    expand_keywords,
    detect_topic,
)
from embeddings import get_embedding_service
from reranker import rerank, get_reranker


def load_benchmark(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def score_all_candidates(
    query: str,
    candidates: list[dict],
) -> tuple[str, list[dict]]:
    """Score all candidates using the existing heuristic, return topic and sorted list."""
    insight = detect_topic(query)
    query_terms = expand_keywords(extract_keywords(query))
    query_embedding = get_embedding_service().encode_one(query)

    scored = []
    for candidate in candidates:
        s, breakdown = score_candidate(
            query_terms, query_embedding, candidate, insight.topic, query.lower()
        )
        c = dict(candidate)
        c["final_score"] = s
        c["score_breakdown"] = breakdown
        scored.append(c)

    scored.sort(key=lambda x: x["final_score"], reverse=True)
    return insight.topic, scored


def build_ranked(result: dict, top_n: int = 5) -> list[str]:
    """Build a ranked section list from a result dict (matches benchmark format)."""
    ranked = []
    primary = result.get("section")
    if primary:
        ranked.append(primary)
    for rule in (result.get("related_rules") or []):
        sec = rule.get("section")
        if sec and sec not in ranked:
            ranked.append(sec)
    for bylaw in (result.get("related_bylaws") or []):
        sec = bylaw.get("section")
        if sec and sec not in ranked:
            ranked.append(sec)
    return ranked[:top_n]


def compute_metrics(
    ranked: list[str], expected: set[str]
) -> dict:
    """Return top-1, top-3, top-5 hit flags and reciprocal rank."""
    top1 = ranked[0] in expected if ranked else False
    top3 = any(s in expected for s in ranked[:3])
    top5 = any(s in expected for s in ranked[:5])
    rr = 0.0
    for rank, sec in enumerate(ranked, start=1):
        if sec in expected:
            rr = 1.0 / rank
            break
    return {"top1": top1, "top3": top3, "top5": top5, "rr": rr}


def run_evaluation(
    benchmark: list[dict],
    use_reranker: bool,
    rerank_k: int = 20,
    profile: bool = False,
) -> dict:
    """Run evaluation. If use_reranker=True, performs cross-encoder reranking on top-k."""
    db = SessionLocal()
    all_candidates = fetch_all_candidates(db)
    db.close()

    total = len(benchmark)
    metrics = {"top1": 0, "top3": 0, "top5": 0, "rrs": []}
    latencies = {"heuristic": [], "rerank": [], "total": []}
    details = []

    # Pre-load reranker if needed (cold start will be counted)
    if use_reranker:
        t0 = time.perf_counter()
        _model = get_reranker()
        t1 = time.perf_counter()
        latencies["rerank_cold"] = (t1 - t0) * 1000

    for i, item in enumerate(benchmark):
        query = item["query"]
        expected = set(item["expected_sections"])
        topic_label = item.get("topic", "?")

        # Step 1: heuristic scoring of all candidates
        t0 = time.perf_counter()
        detected_topic, scored_all = score_all_candidates(query, all_candidates)
        t1 = time.perf_counter()
        heuristic_ms = (t1 - t0) * 1000
        latencies["heuristic"].append(heuristic_ms)

        # Top-20 from heuristic (for reranker input)
        top20 = scored_all[:rerank_k]
        # Heuristic top-5 ranked sections
        heuristic_ranked = [c["section"] for c in scored_all[:5] if c.get("section")]
        heuristic_metrics = compute_metrics(heuristic_ranked, expected)

        # Step 2: reranker (if enabled)
        t2 = time.perf_counter()
        if use_reranker:
            reranked = rerank(query, top20[:], top_k=5)
            rerank_ranked = [c["section"] for c in reranked if c.get("section")]
            rerank_ms = (time.perf_counter() - t2) * 1000
            latencies["rerank"].append(rerank_ms)
        else:
            rerank_ranked = heuristic_ranked
            rerank_ms = 0

        total_ms = heuristic_ms + rerank_ms
        latencies["total"].append(total_ms)

        # Record
        metrics["top1"] += 1 if rerank_ranked and rerank_ranked[0] in expected else 0
        metrics["top3"] += 1 if any(s in expected for s in rerank_ranked[:3]) else 0
        metrics["top5"] += 1 if any(s in expected for s in rerank_ranked[:5]) else 0
        rr = 0.0
        for r, sec in enumerate(rerank_ranked, start=1):
            if sec in expected:
                rr = 1.0 / r
                break
        metrics["rrs"].append(rr)

        details.append({
            "query": query,
            "topic": topic_label,
            "expected": list(expected),
            "heuristic_top5": heuristic_ranked[:5],
            "rerank_top5": rerank_ranked[:5],
            "heuristic_matched": heuristic_metrics["top5"],
            "rerank_matched": any(s in expected for s in rerank_ranked[:5]),
            "rr": rr,
        })

        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{total}", flush=True)

    total_lat = sum(latencies["total"])
    avg_lat = total_lat / total if total else 0

    return {
        "total": total,
        "top1": metrics["top1"],
        "top3": metrics["top3"],
        "top5": metrics["top5"],
        "top1_pct": round(metrics["top1"] / total * 100, 1),
        "top3_pct": round(metrics["top3"] / total * 100, 1),
        "top5_pct": round(metrics["top5"] / total * 100, 1),
        "mrr": round(sum(metrics["rrs"]) / max(len(metrics["rrs"]), 1), 4),
        "avg_latency_ms": round(avg_lat, 1),
        "total_latency_s": round(total_lat / 1000, 1),
        "avg_heuristic_ms": round(sum(latencies["heuristic"]) / total, 1),
        "avg_rerank_ms": round(sum(latencies["rerank"]) / (total or 1), 1) if use_reranker else 0,
        "rerank_cold_ms": round(latencies.get("rerank_cold", 0), 0) if use_reranker else 0,
        "details": details,
    }


def print_results(label: str, stats: dict) -> None:
    print()
    print("=" * 55)
    print(f"  {label}")
    print("=" * 55)
    print(f"  Top-1: {stats['top1']}/{stats['total']} ({stats['top1_pct']}%)")
    print(f"  Top-3: {stats['top3']}/{stats['total']} ({stats['top3_pct']}%)")
    print(f"  Top-5: {stats['top5']}/{stats['total']} ({stats['top5_pct']}%)")
    print(f"  MRR:   {stats['mrr']}")
    print(f"  Avg latency: {stats['avg_latency_ms']}ms")
    if stats.get("avg_heuristic_ms"):
        print(f"    heuristic: {stats['avg_heuristic_ms']}ms")
    if stats.get("avg_rerank_ms"):
        print(f"    reranker:  {stats['avg_rerank_ms']}ms")
    if stats.get("rerank_cold_ms"):
        print(f"    rerank cold start: {stats['rerank_cold_ms']}ms")

    # Per-topic
    topic_stats: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "top1": 0, "top3": 0, "top5": 0, "rrs": []}
    )
    for d in stats["details"]:
        t = d["topic"]
        topic_stats[t]["total"] += 1
        ranked = d["rerank_top5"]
        expected = d["expected"]
        if ranked and ranked[0] in expected:
            topic_stats[t]["top1"] += 1
        if any(s in expected for s in ranked[:3]):
            topic_stats[t]["top3"] += 1
        if any(s in expected for s in ranked[:5]):
            topic_stats[t]["top5"] += 1
        topic_stats[t]["rrs"].append(d["rr"])

    print()
    print(f"  {'Topic':<20} {'Total':<6} {'Top1':<6} {'Top3':<6} {'Top5':<6} {'MRR':<8}")
    print("  " + "-" * 55)
    for t in sorted(topic_stats):
        ts = topic_stats[t]
        mrr_t = round(sum(ts["rrs"]) / max(len(ts["rrs"]), 1), 4)
        print(f"  {t:<20} {ts['total']:<6} {ts['top1']:<6} {ts['top3']:<6} {ts['top5']:<6} {mrr_t:<8}")

    # Mismatches
    print()
    print("  Mismatches (reranker top5):")
    for d in stats["details"]:
        expected = d["expected"]
        ranked = d["rerank_top5"]
        if not any(s in expected for s in ranked[:5]):
            print(f"    {d['topic']:15s} | expected={expected} | top5={ranked[:5]}")
            h_ok = d["heuristic_matched"]
            print(f"                     heuristic matched={h_ok}")
            print(f"                     query: {d['query'][:80]}")
            print()


if __name__ == "__main__":
    bench_path = "/app/tests/retrieval_benchmark.json"
    bench = load_benchmark(bench_path)

    print("=" * 55)
    print("RERANKER EVALUATION")
    print("=" * 55)
    print(f"Benchmark: {len(bench)} queries")
    print(f"Reranker model: cross-encoder/ms-marco-MiniLM-L-6-v2")
    print(f"Rerank candidates: top-20 from heuristic")
    print()

    # ---- Phase 1: Heuristic baseline (no reranker) ----
    print("[Phase 1] Heuristic-only baseline...")
    heur_stats = run_evaluation(bench, use_reranker=False)
    print_results("HEURISTIC SCORING (current)", heur_stats)

    # ---- Phase 2: Heuristic + cross-encoder reranker ----
    print()
    print("[Phase 2] Heuristic + Cross-encoder reranker (top-20)...")
    rerank_stats = run_evaluation(bench, use_reranker=True)
    print_results("HEURISTIC + CROSS-ENCODER RERANKER", rerank_stats)

    # ---- Delta ----
    print()
    print("=" * 55)
    print("  DELTA (reranker - heuristic)")
    print("=" * 55)
    d_top1 = rerank_stats["top1_pct"] - heur_stats["top1_pct"]
    d_top3 = rerank_stats["top3_pct"] - heur_stats["top3_pct"]
    d_top5 = rerank_stats["top5_pct"] - heur_stats["top5_pct"]
    d_mrr = rerank_stats["mrr"] - heur_stats["mrr"]
    print(f"  Top-1: {heur_stats['top1_pct']}% -> {rerank_stats['top1_pct']}% ({d_top1:+.1f}pp)")
    print(f"  Top-3: {heur_stats['top3_pct']}% -> {rerank_stats['top3_pct']}% ({d_top3:+.1f}pp)")
    print(f"  Top-5: {heur_stats['top5_pct']}% -> {rerank_stats['top5_pct']}% ({d_top5:+.1f}pp)")
    print(f"  MRR:   {heur_stats['mrr']} -> {rerank_stats['mrr']} ({d_mrr:+.4f})")
    print()
    print(f"  Latency impact:")
    print(f"    Heuristic:  {heur_stats['avg_latency_ms']}ms avg")
    print(f"    +Reranker:  {rerank_stats['avg_latency_ms']}ms avg ({rerank_stats['avg_rerank_ms']}ms rerank)")
    print(f"    Overhead:   {rerank_stats['avg_rerank_ms'] / max(heur_stats['avg_latency_ms'],1):.1f}x on top of heuristic")
    print()

    # Specific fixes
    fixed = []
    regressed = []
    for hd, rd in zip(heur_stats["details"], rerank_stats["details"]):
        h_match = hd["heuristic_matched"]
        r_match = rd["rerank_matched"]
        if not h_match and r_match:
            fixed.append(rd)
        elif h_match and not r_match:
            regressed.append(rd)

    if fixed:
        print(f"  Queries FIXED by reranker ({len(fixed)}):")
        for d in fixed:
            print(f"    {d['topic']:15s} | expected={d['expected']} | query: {d['query'][:70]}")
    if regressed:
        print(f"  Queries REGRESSED by reranker ({len(regressed)}):")
        for d in regressed:
            print(f"    {d['topic']:15s} | expected={d['expected']} | query: {d['query'][:70]}")

    print()
    print(f"  RECOMMENDATION: ", end="")
    # Decision: keep if meaningful improvement and latency is acceptable
    if d_mrr >= 0.02 and rerank_stats["avg_rerank_ms"] < 200:
        print("KEEP reranker")
    elif d_mrr >= 0.01:
        print("BORDERLINE — MRR gain is small but positive")
    else:
        print("REJECT — insufficient improvement")
