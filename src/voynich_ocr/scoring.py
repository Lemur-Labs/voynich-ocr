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


def loo_cluster_entropy(clusters: np.ndarray, readings: list[list[str]]) -> np.ndarray:
    """Entropy of the transcribers' readings in each instance's cluster, excluding the instance's own readings.

    Leaving the instance out matters: a glyph the transcribers disagree on adds several readings to its own
    cluster, which would raise that cluster's entropy by construction.
    """
    pooled: dict[int, Counter] = {}
    for c, r in zip(clusters, readings):
        pooled.setdefault(int(c), Counter()).update(r)
    out = np.empty(len(readings))
    for i, (c, r) in enumerate(zip(clusters, readings)):
        out[i] = _entropy(pooled[int(c)] - Counter(r))
    return out


def entropy_gap(cluster_entropy: np.ndarray, disagree: np.ndarray) -> Callable[[np.ndarray], float]:
    def statistic(idx: np.ndarray) -> float:
        d = disagree[idx]
        return float(cluster_entropy[idx][d].mean() - cluster_entropy[idx][~d].mean())

    return statistic


def disagreement_auroc(confidence: np.ndarray, disagree: np.ndarray) -> Callable[[np.ndarray], float]:
    def statistic(idx: np.ndarray) -> float:
        return auroc(1.0 - confidence[idx], disagree[idx])

    return statistic


def decide_clusters(gap: Interval) -> str:
    return "pass" if gap.lo > 0 else "kill"


def decide_recognizer(full: Interval, leave_zl_out: Interval) -> str:
    full_ok, loo_ok = full.lo > 0.5, leave_zl_out.lo > 0.5
    if full_ok and loo_ok:
        return "pass"
    if full_ok or loo_ok:
        return "narrow"
    return "kill"
