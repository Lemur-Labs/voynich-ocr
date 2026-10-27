import numpy as np
import pytest

from voynich_ocr import scoring
from voynich_ocr.scoring import Interval

RESAMPLES = 300


def test_auroc_is_one_when_every_positive_outranks_every_negative():
    assert scoring.auroc(np.array([0.1, 0.2, 0.8, 0.9]), np.array([0, 0, 1, 1])) == 1.0


def test_auroc_counts_ties_as_half():
    assert scoring.auroc(np.array([0.5, 0.5, 0.5, 0.5]), np.array([0, 1, 0, 1])) == 0.5


def test_auroc_matches_the_pairwise_definition():
    rng = np.random.default_rng(1)
    s = rng.integers(0, 5, 200).astype(float)
    y = rng.random(200) < 0.3
    pos, neg = s[y], s[~y]
    pairwise = ((pos[:, None] > neg[None, :]) + 0.5 * (pos[:, None] == neg[None, :])).mean()
    assert scoring.auroc(s, y) == pytest.approx(pairwise)


def test_auroc_refuses_a_single_class():
    with pytest.raises(ValueError):
        scoring.auroc(np.array([0.1, 0.2]), np.array([1, 1]))


def test_ece_is_near_zero_for_a_calibrated_predictor_and_large_for_an_overconfident_one():
    rng = np.random.default_rng(2)
    conf = rng.uniform(0.2, 1.0, 20000)
    calibrated = rng.random(conf.size) < conf
    overconfident = rng.random(conf.size) < conf * 0.6
    assert scoring.ece(conf, calibrated) < 0.02
    assert scoring.ece(conf, overconfident) > 0.2


def _glyphs(n_pages=60, per_page=80, seed=3):
    rng = np.random.default_rng(seed)
    pages = np.repeat(np.arange(n_pages), per_page)
    page_difficulty = rng.uniform(0.05, 0.4, n_pages)[pages]
    disagree = rng.random(pages.size) < page_difficulty
    return rng, pages, disagree


def test_recognizer_scorer_finds_confidence_that_drops_where_transcribers_disagree():
    rng, pages, disagree = _glyphs()
    confidence = np.clip(rng.normal(0.85, 0.08, pages.size) - 0.15 * disagree, 0, 1)
    ci = scoring.page_bootstrap(scoring.disagreement_auroc(confidence, disagree), pages, RESAMPLES)
    assert ci.lo > 0.5


def test_recognizer_scorer_stays_null_when_confidence_ignores_disagreement():
    rng, pages, disagree = _glyphs()
    confidence = np.clip(rng.normal(0.85, 0.08, pages.size), 0, 1)
    ci = scoring.page_bootstrap(scoring.disagreement_auroc(confidence, disagree), pages, RESAMPLES)
    assert ci.lo <= 0.5 <= ci.hi


def test_page_bootstrap_is_wider_than_a_glyph_bootstrap_when_pages_cluster():
    rng, pages, disagree = _glyphs()
    page_effect = rng.normal(0, 0.1, pages.max() + 1)[pages]
    confidence = np.clip(0.8 + page_effect - 0.05 * disagree, 0, 1)
    stat = scoring.disagreement_auroc(confidence, disagree)
    by_page = scoring.page_bootstrap(stat, pages, RESAMPLES)
    by_glyph = scoring.page_bootstrap(stat, np.arange(pages.size), RESAMPLES)
    assert by_page.hi - by_page.lo > by_glyph.hi - by_glyph.lo


def test_page_bootstrap_is_deterministic_under_the_pinned_seed():
    rng, pages, disagree = _glyphs()
    confidence = rng.random(pages.size)
    stat = scoring.disagreement_auroc(confidence, disagree)
    assert scoring.page_bootstrap(stat, pages, 50) == scoring.page_bootstrap(stat, pages, 50)


def _clustered_glyphs(seed=4, ambiguous_share=0.3, inject=True):
    rng = np.random.default_rng(seed)
    n_pages, per_page, n_clusters = 50, 60, 20
    pages = np.repeat(np.arange(n_pages), per_page)
    clusters = rng.integers(0, n_clusters, pages.size)
    ambiguous = clusters < int(n_clusters * ambiguous_share)
    readings, disagree = [], np.zeros(pages.size, dtype=bool)
    for i, c in enumerate(clusters):
        base = f"g{c}"
        if inject and ambiguous[i] and rng.random() < 0.6 or not inject and rng.random() < 0.18:
            readings.append([base, base, f"g{c}x"])
            disagree[i] = True
        else:
            readings.append([base, base, base])
    return pages, clusters, readings, disagree


def test_cluster_scorer_finds_disagreement_concentrated_in_ambiguous_clusters():
    pages, clusters, readings, disagree = _clustered_glyphs(inject=True)
    h = scoring.loo_cluster_entropy(clusters, readings)
    ci = scoring.page_bootstrap(scoring.entropy_gap(h, disagree), pages, RESAMPLES)
    assert scoring.decide_clusters(ci) == "pass"


def test_cluster_scorer_stays_null_when_disagreement_is_spread_evenly_across_clusters():
    pages, clusters, readings, disagree = _clustered_glyphs(inject=False)
    h = scoring.loo_cluster_entropy(clusters, readings)
    ci = scoring.page_bootstrap(scoring.entropy_gap(h, disagree), pages, RESAMPLES)
    assert scoring.decide_clusters(ci) == "kill"


def test_cluster_entropy_excludes_the_instances_own_readings():
    clusters = np.array([0, 0])
    readings = [["a", "b"], ["a", "a"]]
    h = scoring.loo_cluster_entropy(clusters, readings)
    assert h[0] == 0.0
    assert h[1] == 1.0


@pytest.mark.parametrize(
    ("full", "loo", "verdict"),
    [
        (Interval(0.6, 0.55, 0.65), Interval(0.58, 0.52, 0.63), "pass"),
        (Interval(0.6, 0.55, 0.65), Interval(0.52, 0.48, 0.57), "narrow"),
        (Interval(0.52, 0.49, 0.56), Interval(0.51, 0.47, 0.55), "kill"),
        (Interval(0.6, 0.50, 0.65), Interval(0.6, 0.50, 0.65), "kill"),
    ],
)
def test_recognizer_gate_rule(full, loo, verdict):
    assert scoring.decide_recognizer(full, loo) == verdict
