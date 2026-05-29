"""Pure-function tests for intelligence.py — no I/O, no DB, no Redis."""
import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import llm
from app.services.intelligence import (
    TARGET_SOLVED,
    WEAK_THRESHOLD,
    CORE_TOPICS,
    TOPIC_WEIGHTS,
    compute_weakness_score,
    normalize_lc_topic,
    compute_readiness_score,
    aggregate_lc_topics,
)


# ── compute_weakness_score ─────────────────────────────────────────────────────

def test_weakness_more_solved_means_lower_score():
    low = compute_weakness_score("arrays", 2)
    high = compute_weakness_score("arrays", 15)
    assert low > high


def test_weakness_fully_covered_is_near_zero():
    score = compute_weakness_score("arrays", TARGET_SOLVED)
    assert score == 0.0


def test_weakness_exceeding_target_clamps_to_zero():
    score = compute_weakness_score("arrays", TARGET_SOLVED + 50)
    assert score == 0.0


def test_weakness_higher_weight_topic_scores_higher_at_same_solves():
    dp_score = compute_weakness_score("dynamic-programming", 0)
    math_score = compute_weakness_score("math", 0)
    assert dp_score > math_score


def test_weakness_bounded_between_zero_and_one():
    for topic in TOPIC_WEIGHTS:
        for solved in (0, 1, 10, 20, 50):
            s = compute_weakness_score(topic, solved)
            assert 0.0 <= s <= 1.0, f"{topic} solved={solved} → {s}"


def test_weakness_zero_solved_returns_importance():
    from app.services.intelligence import _MAX_WEIGHT
    importance = TOPIC_WEIGHTS["graphs"] / _MAX_WEIGHT
    assert compute_weakness_score("graphs", 0) == round(importance, 4)


# ── normalize_lc_topic ────────────────────────────────────────────────────────

def test_normalize_known_slugs():
    assert normalize_lc_topic("binary-tree") == "trees"
    assert normalize_lc_topic("array") == "arrays"
    assert normalize_lc_topic("hash-table") == "hashing"
    assert normalize_lc_topic("dynamic-programming") == "dynamic-programming"
    assert normalize_lc_topic("brainteaser") == "math"


def test_normalize_unknown_returns_none():
    assert normalize_lc_topic("unknown-tag-xyz") is None
    assert normalize_lc_topic("") is None


# ── compute_readiness_score ───────────────────────────────────────────────────

def _make_ts(topic, weakness):
    return {"topic": topic, "weakness_score": weakness}


def test_readiness_keys_present():
    result = compute_readiness_score(0, 0, 0, 0, 0, [], 0, 1)
    assert "total" in result
    assert set(result["breakdown"]) == {"dsa_consistency", "github_activity", "topic_coverage", "sheet_progress"}


def test_readiness_well_covered_core_gives_high_coverage():
    topic_scores = [_make_ts(t, 0.0) for t in CORE_TOPICS]
    result = compute_readiness_score(0, 0, 0, 0, 0, topic_scores, 0, 1)
    assert result["breakdown"]["topic_coverage"] == 100.0


def test_readiness_sparse_core_gives_low_coverage():
    topic_scores = [_make_ts(t, 1.0) for t in CORE_TOPICS]
    result = compute_readiness_score(0, 0, 0, 0, 0, topic_scores, 0, 1)
    assert result["breakdown"]["topic_coverage"] == 0.0


def test_readiness_absent_topic_treated_as_uncovered():
    result = compute_readiness_score(0, 0, 0, 0, 0, [], 0, 1)
    assert result["breakdown"]["topic_coverage"] == 0.0


def test_readiness_weak_threshold_boundary():
    just_below = [_make_ts(t, WEAK_THRESHOLD - 0.01) for t in CORE_TOPICS]
    just_above = [_make_ts(t, WEAK_THRESHOLD) for t in CORE_TOPICS]
    below = compute_readiness_score(0, 0, 0, 0, 0, just_below, 0, 1)
    above = compute_readiness_score(0, 0, 0, 0, 0, just_above, 0, 1)
    assert below["breakdown"]["topic_coverage"] == 100.0
    assert above["breakdown"]["topic_coverage"] == 0.0


def test_readiness_math_adds_up():
    ts = [_make_ts(t, 0.0) for t in CORE_TOPICS]
    result = compute_readiness_score(100, 50, 10, 100, 3, ts, 50, 100)
    breakdown = result["breakdown"]
    expected = round(
        0.35 * breakdown["dsa_consistency"] / 100 * 100
        + 0.25 * breakdown["github_activity"] / 100 * 100
        + 0.30 * breakdown["topic_coverage"] / 100 * 100
        + 0.10 * breakdown["sheet_progress"] / 100 * 100,
        1,
    )
    assert result["total"] == expected


# ── aggregate_lc_topics ───────────────────────────────────────────────────────

def test_aggregate_collapses_multiple_slugs_to_one_topic():
    raw = {
        "easy": [
            {"tagSlug": "tree", "problemsSolved": 5},
            {"tagSlug": "binary-tree", "problemsSolved": 3},
        ]
    }
    result = aggregate_lc_topics(raw)
    assert result["trees"] == 8


def test_aggregate_skips_unmapped_slugs():
    raw = {
        "easy": [
            {"tagSlug": "unknown-tag", "problemsSolved": 10},
            {"tagSlug": "array", "problemsSolved": 7},
        ]
    }
    result = aggregate_lc_topics(raw)
    assert "arrays" in result
    assert result["arrays"] == 7
    assert "unknown-tag" not in result


def test_aggregate_sums_across_difficulty_groups():
    raw = {
        "easy": [{"tagSlug": "array", "problemsSolved": 10}],
        "medium": [{"tagSlug": "array", "problemsSolved": 20}],
        "hard": [{"tagSlug": "array", "problemsSolved": 5}],
    }
    result = aggregate_lc_topics(raw)
    assert result["arrays"] == 35


def test_aggregate_empty_input():
    assert aggregate_lc_topics({}) == {}


# ── LLM resilience (no Redis/network: _call_llm monkeypatched, cache is a no-op) ──

def test_recommend_formats_slugs(monkeypatch):
    async def fake_call(_prompt):
        return '["two-sum", "lc-3sum", "valid-parentheses"]'
    monkeypatch.setattr(llm, "_call_llm", fake_call)
    out = asyncio.run(llm.recommend_next_problems(["arrays"], set()))
    assert out == ["lc-two-sum", "lc-3sum", "lc-valid-parentheses"]


def test_recommend_returns_empty_without_caching_on_failure(monkeypatch):
    # Provider failure (e.g. 429) must degrade to [] and NOT poison the cache.
    async def boom(_prompt):
        raise RuntimeError("429 quota exceeded")
    cached = {}
    monkeypatch.setattr(llm, "_call_llm", boom)
    monkeypatch.setattr(llm, "set_cached", lambda *a, **k: cached.setdefault("written", True))
    out = asyncio.run(llm.recommend_next_problems(["arrays"], set()))
    assert out == []
    assert "written" not in cached  # empty result was never cached


def test_summarize_readiness_empty_not_cached(monkeypatch):
    async def boom(_prompt):
        raise RuntimeError("429")
    cached = {}
    monkeypatch.setattr(llm, "_call_llm", boom)
    monkeypatch.setattr(llm, "set_cached", lambda *a, **k: cached.setdefault("written", True))
    out = asyncio.run(llm.summarize_readiness({"dsa_consistency": 50}))
    assert out == ""
    assert "written" not in cached
