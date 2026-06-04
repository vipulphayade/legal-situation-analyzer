"""Evaluate query understanding accuracy.

Usage: python tests/_eval_query_understanding.py

Measures per-field accuracy, strategy selection, and reports
failure clusters (by topic, by field).
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from collections import Counter, defaultdict
from query_understanding import detect_topic
from retrieval_strategy import select_strategy


FIELDS = ["intent", "actor", "action", "subject", "topic", "section_ref", "strategy"]


def load_benchmark(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_eval(benchmark: list[dict]) -> dict:
    total = len(benchmark)
    field_correct: dict[str, int] = {f: 0 for f in FIELDS}
    topic_failures: dict[str, list[str]] = defaultdict(list)
    field_failures: dict[str, list[dict]] = defaultdict(list)
    all_correct = 0

    for item in benchmark:
        query = item["query"]
        insight = detect_topic(query)
        actual_strategy = select_strategy(insight).value if hasattr(select_strategy(insight), "value") else str(select_strategy(insight))

        ok = True
        for field in FIELDS:
            expected = item.get(field, "")
            if field == "strategy":
                actual = actual_strategy
            elif field == "section_ref":
                actual = insight.section_ref
            else:
                actual = getattr(insight, field, "")
            if actual == expected:
                field_correct[field] += 1
            else:
                ok = False
                field_failures[field].append({
                    "query": query,
                    "expected": expected,
                    "actual": actual,
                })
        if ok:
            all_correct += 1
        else:
            topic = insight.topic or "unknown"
            topic_failures[topic].append(query)

    total_field = len(benchmark)
    field_accuracy = {f: round(field_correct[f] / total_field * 100, 1) for f in FIELDS}
    overall = round(all_correct / total * 100, 1)

    return {
        "total": total,
        "all_correct": all_correct,
        "overall_accuracy": overall,
        "field_accuracy": field_accuracy,
        "field_failures": {
            f: sorted(fails, key=lambda x: x["query"])
            for f, fails in field_failures.items()
        },
        "topic_failures": dict(topic_failures),
        "failure_count_by_topic": {t: len(qs) for t, qs in sorted(topic_failures.items(), key=lambda x: -len(x[1]))},
    }


def print_report(result: dict) -> None:
    print(f"Query Understanding Benchmark")
    print(f"{'=' * 50}")
    print(f"Total queries: {result['total']}")
    print(f"All fields correct: {result['all_correct']} ({result['overall_accuracy']}%)")
    print()

    print(f"Per-field accuracy:")
    for field, acc in sorted(result["field_accuracy"].items(), key=lambda x: -x[1]):
        bar = "#" * int(acc / 5)
        print(f"  {field:15s} {acc:5.1f}%  {bar}")
    print()

    failures = result["field_failures"]
    total_fails = sum(len(v) for v in failures.values())
    if total_fails:
        print(f"Total field-level failures: {total_fails}")
        for field, fails in sorted(failures.items(), key=lambda x: -len(x[1])):
            if fails:
                print(f"\n  Field: {field} ({len(fails)} failures)")
                for f in fails:
                    print(f"    Q: {f['query']}")
                    print(f"       expected={f['expected']!r}, actual={f['actual']!r}")
        print()
    else:
        print("No field failures.")
        print()

    topic_fails = result.get("failure_count_by_topic", {})
    if topic_fails:
        print(f"Failures by topic:")
        for topic, count in topic_fails.items():
            bar = "#" * count
            print(f"  {topic:15s} {count:3d}  {bar}")


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "query_understanding_benchmark.json")
    benchmark = load_benchmark(path)
    result = run_eval(benchmark)
    print_report(result)

    # Return non-zero if any field is below 70%
    min_ok = all(acc >= 70.0 for acc in result["field_accuracy"].values())
    sys.exit(0 if min_ok else 1)
