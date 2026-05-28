"""Topic weakness score + interview readiness score computation."""
from typing import Optional, Dict

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

TARGET_SOLVED = 20
_MAX_WEIGHT = max(TOPIC_WEIGHTS.values())  # 1.4
WEAK_THRESHOLD = 0.4

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


def aggregate_lc_topics(tag_problem_counts: dict) -> Dict[str, int]:
    """Collapse raw LC tagProblemCounts (by difficulty group) into canonical topic → solved."""
    agg: Dict[str, int] = {}
    for difficulty_group in tag_problem_counts.values():
        for tag_data in difficulty_group:
            canon = normalize_lc_topic(tag_data.get("tagSlug", ""))
            if canon is None:
                continue
            agg[canon] = agg.get(canon, 0) + tag_data.get("problemsSolved", 0)
    return agg


def compute_weakness_score(topic: str, solved: int) -> float:
    """Higher score = weaker: important topics with few solved problems rank highest."""
    mastery = min(solved / TARGET_SOLVED, 1.0)
    importance = TOPIC_WEIGHTS.get(topic, 1.0) / _MAX_WEIGHT
    return round(importance * (1.0 - mastery), 4)


def compute_readiness_score(
    lc_easy: int, lc_medium: int, lc_hard: int,
    cf_solved: int,
    github_active_repos: int,
    topic_scores: list,
    sheet_done: int, sheet_total: int,
) -> dict:
    # DSA Consistency (35%)
    lc_dsa = min((lc_easy * 1 + lc_medium * 2 + lc_hard * 3) / 300, 1.0)
    cf_dsa = min(cf_solved / 200, 1.0)
    dsa_score = (lc_dsa + cf_dsa) / 2

    # GitHub Activity (25%)
    gh_score = min(github_active_repos / 3, 1.0)

    # Topic Coverage (30%): covered = weakness low (well-solved), absent = weakness 1.0 (never touched)
    strong_core = sum(
        1 for ts in topic_scores
        if ts["topic"] in CORE_TOPICS
        and (ts.get("weakness_score") if ts.get("weakness_score") is not None else 1.0) < WEAK_THRESHOLD
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
