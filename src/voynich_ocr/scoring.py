from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 20261026


@dataclass(frozen=True)
class Interval:
    point: float
    lo: float
    hi: float


def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Probability a random positive outranks a random negative; ties count half."""
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=bool)
    n_pos = int(labels.sum())
    n_neg = labels.size - n_pos
    if n_pos == 0 or n_neg == 0:
        raise ValueError("auroc needs both classes")
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(scores.size)
    sorted_scores = scores[order]
    i = 0
    while i < scores.size:
        j = i
        while j + 1 < scores.size and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return (ranks[labels].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def ece(confidence: np.ndarray, correct: np.ndarray, bins: int = 15) -> float:
    confidence = np.asarray(confidence, dtype=float)
    correct = np.asarray(correct, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    idx = np.clip(np.digitize(confidence, edges[1:-1], right=True), 0, bins - 1)
    total = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            total += m.sum() * abs(confidence[m].mean() - correct[m].mean())
    return total / confidence.size


def page_bootstrap(
    statistic: Callable[[np.ndarray], float],
    pages: np.ndarray,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> Interval:
    """95% percentile interval, resampling whole pages: glyphs on one page are not independent.

    `statistic` takes an index array into the glyph-level data and returns a number.
    """
    pages = np.asarray(pages)
    unique = np.unique(pages)
    members = [np.flatnonzero(pages == p) for p in unique]
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(resamples):
        chosen = rng.integers(0, unique.size, unique.size)
        draws.append(statistic(np.concatenate([members[k] for k in chosen])))
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return Interval(statistic(np.arange(pages.size)), float(lo), float(hi))


def _entropy(counts: Counter) -> float:
    n = sum(counts.values())
    if n == 0:
        return 0.0
    p = np.array([c / n for c in counts.values() if c > 0])
    return float(-(p * np.log2(p)).sum())


def loo_cluster_entropy(clusters: np.ndarray, readings: list[list[str]], pages: np.ndarray) -> np.ndarray:
    """Entropy of the transcribers' readings in each instance's cluster, excluding every instance on its page.

    Excluding the instance matters: a glyph the transcribers disagree on adds several readings to its own cluster,
    raising that cluster's entropy by construction. Excluding the whole page matters too: repeated words carry
    one transcriber's convention for that page into the cluster.
    """
    pooled: dict[int, Counter] = {}
    same_page: dict[tuple[int, object], Counter] = {}
    for c, r, p in zip(clusters, readings, pages):
        pooled.setdefault(int(c), Counter()).update(r)
        same_page.setdefault((int(c), p), Counter()).update(r)
    out = np.empty(len(readings))
    for i, (c, p) in enumerate(zip(clusters, pages)):
        out[i] = _entropy(pooled[int(c)] - same_page[(int(c), p)])
    return out


def _gap(h: np.ndarray, d: np.ndarray) -> float:
    return float(h[d].mean() - h[~d].mean())


def within_stratum_gap(
    cluster_entropy: np.ndarray, disagree: np.ndarray, strata: np.ndarray
) -> Callable[[np.ndarray], float]:
    """Entropy gap computed inside each stratum (the ZL token) and weighted by instance count.

    Pooled over all tokens, the gap is positive whenever some tokens are disputed more than others, which the
    text alone shows; within a token, only the images can separate disputed instances from undisputed ones.
    """

    def statistic(idx: np.ndarray) -> float:
        h, d, s = cluster_entropy[idx], disagree[idx], strata[idx]
        total, weight = 0.0, 0
        for key in np.unique(s):
            m = s == key
            if d[m].any() and (~d[m]).any():
                total += m.sum() * _gap(h[m], d[m])
                weight += m.sum()
        return total / weight if weight else 0.0

    return statistic


def permutation_null(
    statistic_for: Callable[[np.ndarray], Callable[[np.ndarray], float]],
    disagree: np.ndarray,
    pages: np.ndarray,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> float:
    """97.5th percentile of the statistic with `disagree` shuffled within each page."""
    rng = np.random.default_rng(seed)
    members = [np.flatnonzero(pages == p) for p in np.unique(pages)]
    everything = np.arange(disagree.size)
    draws = []
    for _ in range(resamples):
        shuffled = disagree.copy()
        for m in members:
            shuffled[m] = disagree[rng.permutation(m)]
        draws.append(statistic_for(shuffled)(everything))
    return float(np.percentile(draws, 97.5))


def auroc_statistic(scores: np.ndarray, disagree: np.ndarray) -> Callable[[np.ndarray], float]:
    """Higher score should mean more likely disputed: pass 1 - confidence, or a baseline score."""

    def statistic(idx: np.ndarray) -> float:
        return auroc(scores[idx], disagree[idx])

    return statistic


def within_group_auroc(
    scores: np.ndarray,
    disagree: np.ndarray,
    groups: np.ndarray,
    min_pos: int,
    min_neg: int,
    weighted: bool,
) -> Callable[[np.ndarray], float]:
    """Mean of per-group AUROCs over groups with enough of both classes; glyph-weighted when `weighted`."""

    def statistic(idx: np.ndarray) -> float:
        sc, d, g = scores[idx], disagree[idx], groups[idx]
        values, weights = [], []
        for key in np.unique(g):
            m = g == key
            pos = int(d[m].sum())
            if pos >= min_pos and m.sum() - pos >= min_neg:
                values.append(auroc(sc[m], d[m]))
                weights.append(m.sum() if weighted else 1)
        if not values:
            return 0.5
        return float(np.average(values, weights=weights))

    return statistic


TYPE_MIN_POS, TYPE_MIN_NEG = 20, 20
PAGE_MIN_POS, PAGE_MIN_NEG = 10, 1


def within_type_auroc(scores: np.ndarray, disagree: np.ndarray, tokens: np.ndarray):
    return within_group_auroc(scores, disagree, tokens, TYPE_MIN_POS, TYPE_MIN_NEG, weighted=True)


def within_page_auroc(scores: np.ndarray, disagree: np.ndarray, pages: np.ndarray):
    return within_group_auroc(scores, disagree, pages, PAGE_MIN_POS, PAGE_MIN_NEG, weighted=False)


def group_coverage(disagree: np.ndarray, groups: np.ndarray, min_pos: int, min_neg: int) -> float:
    """Share of glyphs in groups with enough of both classes to be scored."""
    disagree = np.asarray(disagree, dtype=bool)
    covered = 0
    for key in np.unique(groups):
        m = groups == key
        pos = int(disagree[m].sum())
        if pos >= min_pos and m.sum() - pos >= min_neg:
            covered += int(m.sum())
    return covered / disagree.size


def within_type_coverage(disagree: np.ndarray, tokens: np.ndarray) -> float:
    return group_coverage(disagree, tokens, TYPE_MIN_POS, TYPE_MIN_NEG)


def within_page_coverage(disagree: np.ndarray, pages: np.ndarray) -> float:
    return group_coverage(disagree, pages, PAGE_MIN_POS, PAGE_MIN_NEG)


MAX_TEST_ATTRITION = 0.25


def void_for_attrition(kept: int, total: int) -> bool:
    return kept < (1 - MAX_TEST_ATTRITION) * total


# docs/prereg.md amendment A1.
MIN_GROUP_COVERAGE: float | None = 0.72


def void_for_underpower(coverage: float, minimum: float | None = MIN_GROUP_COVERAGE) -> bool:
    if minimum is None:
        raise RuntimeError("MIN_GROUP_COVERAGE must be fixed from non-test pages before the gate runs")
    return coverage < minimum


def decide_clusters(within_token_gap: Interval, null_975: float, control_point: float) -> str:
    if within_token_gap.lo <= null_975:
        return "kill"
    return "narrow" if control_point * within_token_gap.point < 0 else "pass"


def decide_recognizer(
    within_type_full: Interval,
    within_type_leave_zl_out: Interval,
    within_page_full: Interval,
    best_within_type_baseline_point: float,
) -> str:
    """Full-map pass requires within-page signal, and within-type signal above chance and above the best baseline
    that varies within a type (span width, page-mean confidence)."""
    type_bar = max(0.5, best_within_type_baseline_point)
    full_ok = within_type_full.lo > type_bar and within_page_full.lo > 0.5
    loo_ok = within_type_leave_zl_out.lo > 0.5
    if full_ok and loo_ok:
        return "pass"
    if full_ok:
        return "narrow"
    return "kill"
