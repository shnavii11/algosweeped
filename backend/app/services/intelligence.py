"""Topic weakness score + interview readiness score computation."""
import math
from typing import Optional

TOPIC_WEIGHTS = {
    "dynamic-programming": 1.4,
    "graphs": 1.3,
    "trees": 1.2,
    "binary-search": 1.1,
    "arrays": 1.0,
    "strings": 1.0,
    "greedy": 0.9,
    "math": 0.8,
}

CORE_TOPICS = ["dynamic-programming", "graphs", "trees", "binary-search", "arrays", "strings"]

# Inline mirror of scripts/lib/lc_topic_map.json — keeps the backend self-contained
# for deploy (LeetCode raw tag-slugs → canonical 22-topic taxonomy).
LC_TAG_TO_TOPIC = {
    "array": "arrays",
    "string": "strings",
    "hash-table": "hashing",
    "hash-map": "hashing",
    "two-pointers": "two-pointers",
    "sliding-window": "sliding-window",
    "prefix-sum": "prefix-sum",
    "binary-search": "binary-search",
    "linked-list": "linked-list",
    "stack": "stacks-queues",
    "queue": "stacks-queues",
    "monotonic-stack": "stacks-queues",
    "monotonic-queue": "stacks-queues",
    "recursion": "recursion",
    "divide-and-conquer": "recursion",
    "backtracking": "backtracking",
    "tree": "trees",
    "binary-tree": "trees",
    "depth-first-search": "trees",
    "breadth-first-search": "trees",
    "binary-search-tree": "bst",
    "heap-priority-queue": "heap",
    "greedy": "greedy",
    "dynamic-programming": "dynamic-programming",
    "memoization": "dynamic-programming",
    "graph": "graphs",
    "topological-sort": "graphs",
    "union-find": "graphs",
    "shortest-path": "graphs",
    "trie": "tries",
    "segment-tree": "segment-trees",
    "binary-indexed-tree": "segment-trees",
    "bit-manipulation": "bit-manipulation",
    "math": "math",
    "number-theory": "math",
    "combinatorics": "math",
    "string-matching": "string-algorithms",
    "suffix-array": "string-algorithms",
    "sorting": "arrays",
    "matrix": "arrays",
    "simulation": "arrays",
    "counting": "math",
    "enumeration": "arrays",
    "geometry": "math",
    "game-theory": "dynamic-programming",
    "interactive": "arrays",
    "brainteaser": "math",
    "design": "stacks-queues",
    "iterator": "stacks-queues",
    "ordered-set": "bst",
    "randomized": "math",
    "rolling-hash": "hashing",
    "hash-function": "hashing",
}


def normalize_lc_topic(raw: str) -> Optional[str]:
    """Map a raw LeetCode tag-slug to a canonical topic, or None if unmapped."""
    return LC_TAG_TO_TOPIC.get(raw)


def compute_weakness_score(topic: str, solved: int, attempted: int) -> float:
    accuracy = solved / max(attempted, 1)
    volume_bonus = min(solved / 20, 1.0)
    raw = 0.7 * accuracy + 0.3 * volume_bonus
    weight = TOPIC_WEIGHTS.get(topic, 1.0)
    return round(raw / weight, 4)


def compute_readiness_score(
    lc_easy: int, lc_medium: int, lc_hard: int,
    cf_solved: int,
    github_active_repos: int,
    topic_scores: list[dict],
    sheet_done: int, sheet_total: int,
) -> dict:
    # DSA Consistency (35%)
    lc_dsa = min((lc_easy * 1 + lc_medium * 2 + lc_hard * 3) / 300, 1.0)
    cf_dsa = min(cf_solved / 200, 1.0)
    dsa_score = (lc_dsa + cf_dsa) / 2

    # GitHub Activity (25%)
    gh_score = min(github_active_repos / 3, 1.0)

    # Topic Coverage (30%)
    strong_core = sum(
        1 for ts in topic_scores
        if ts["topic"] in CORE_TOPICS and (ts.get("weakness_score") or 0) > 0.5
    )
    coverage_score = strong_core / len(CORE_TOPICS)

    # Sheet Progress (10%)
    sheet_score = sheet_done / max(sheet_total, 1)

    total = (
        0.35 * dsa_score +
        0.25 * gh_score +
        0.30 * coverage_score +
        0.10 * sheet_score
    ) * 100

    return {
        "total": round(total, 1),
        "breakdown": {
            "dsa_consistency": round(dsa_score * 100, 1),
            "github_activity": round(gh_score * 100, 1),
            "topic_coverage": round(coverage_score * 100, 1),
            "sheet_progress": round(sheet_score * 100, 1),
        },
    }
