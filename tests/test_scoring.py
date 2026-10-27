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


def _glyphs(n_pages=60, per_page=200, n_tokens=8, seed=3):
    rng = np.random.default_rng(seed)
    pages = np.repeat(np.arange(n_pages), per_page)
    tokens = rng.integers(0, n_tokens, pages.size)
    return rng, pages, tokens


def _ci(stat, pages):
    return scoring.page_bootstrap(stat, pages, RESAMPLES)


def test_within_type_auroc_finds_instance_level_signal():
    rng, pages, tokens = _glyphs()
    disagree = rng.random(pages.size) < 0.25
    confidence = np.clip(rng.normal(0.85, 0.08, pages.size) - 0.12 * disagree, 0, 1)
    assert _ci(scoring.within_type_auroc(1 - confidence, disagree, tokens), pages).lo > 0.5


def test_glyph_type_alone_inflates_pooled_auroc_but_not_within_type_auroc():
    rng, pages, tokens = _glyphs()
    disputed_type = tokens < 3
    disagree = rng.random(pages.size) < np.where(disputed_type, 0.5, 0.1)
    confidence = np.clip(rng.normal(0.85, 0.05, pages.size) - 0.2 * disputed_type, 0, 1)
    pooled = _ci(scoring.auroc_statistic(1 - confidence, disagree), pages)
    within = _ci(scoring.within_type_auroc(1 - confidence, disagree, tokens), pages)
    assert pooled.lo > 0.5
    assert within.lo <= 0.5 <= within.hi


def test_page_quality_alone_inflates_pooled_auroc_but_not_within_page_auroc():
    rng, pages, _ = _glyphs()
    badness = rng.uniform(0, 1, pages.max() + 1)[pages]
    disagree = rng.random(pages.size) < 0.05 + 0.4 * badness
    confidence = np.clip(0.95 - 0.3 * badness + rng.normal(0, 0.03, pages.size), 0, 1)
    pooled = _ci(scoring.auroc_statistic(1 - confidence, disagree), pages)
    within = _ci(scoring.within_page_auroc(1 - confidence, disagree, pages), pages)
    assert pooled.lo > 0.5
    assert within.lo <= 0.5 <= within.hi


def test_page_bootstrap_is_wider_than_a_glyph_bootstrap_when_pages_cluster():
    rng, pages, _ = _glyphs()
    disagree = rng.random(pages.size) < 0.2
    page_effect = rng.normal(0, 0.1, pages.max() + 1)[pages]
    confidence = np.clip(0.8 + page_effect - 0.05 * disagree, 0, 1)
    stat = scoring.auroc_statistic(1 - confidence, disagree)
    by_page = _ci(stat, pages)
    by_glyph = _ci(stat, np.arange(pages.size))
    assert by_page.hi - by_page.lo > by_glyph.hi - by_glyph.lo


def test_page_bootstrap_is_deterministic_under_the_pinned_seed():
    rng, pages, _ = _glyphs()
    disagree = rng.random(pages.size) < 0.2
    stat = scoring.auroc_statistic(rng.random(pages.size), disagree)
    assert scoring.page_bootstrap(stat, pages, 50) == scoring.page_bootstrap(stat, pages, 50)


def _clustered(image_signal: bool, seed=4):
    """Each instance has a ZL token; half of tokens are disputed more often (a fact the text alone shows).

    With `image_signal`, disputed instances of a token also look different, landing in a mixed cluster.
    """
    rng = np.random.default_rng(seed)
    n_pages, per_page, n_tokens = 40, 120, 10
    pages = np.repeat(np.arange(n_pages), per_page)
    tokens = rng.integers(0, n_tokens, pages.size)
    disagree = rng.random(pages.size) < np.where(tokens < n_tokens // 2, 0.4, 0.1)
    readings = [[f"t{t}", f"t{t}", f"t{t}x" if d else f"t{t}"] for t, d in zip(tokens, disagree)]
    clusters = tokens * 2 + (disagree if image_signal else rng.random(pages.size) < 0.3)
    return pages, tokens, clusters.astype(int), readings, disagree


def _cluster_verdict(pages, tokens, clusters, readings, disagree):
    h = scoring.loo_cluster_entropy(clusters, readings, pages)
    gap = _ci(scoring.within_stratum_gap(h, disagree, tokens), pages)
    null = scoring.permutation_null(
        lambda d: scoring.within_stratum_gap(h, d, tokens), disagree, pages, resamples=200
    )
    return scoring.decide_clusters(gap, null, control_point=gap.point)


def test_cluster_scorer_passes_when_images_separate_disputed_instances_within_a_token():
    assert _cluster_verdict(*_clustered(image_signal=True)) == "pass"


def test_cluster_scorer_kills_when_only_the_token_predicts_disagreement():
    assert _cluster_verdict(*_clustered(image_signal=False)) == "kill"


def test_cluster_gate_narrows_when_the_label_free_control_points_the_other_way():
    gap = Interval(0.2, 0.1, 0.3)
    assert scoring.decide_clusters(gap, 0.05, control_point=0.15) == "pass"
    assert scoring.decide_clusters(gap, 0.05, control_point=-0.02) == "narrow"
    assert scoring.decide_clusters(gap, 0.12, control_point=0.15) == "kill"


def test_cluster_entropy_excludes_every_instance_on_the_same_page():
    clusters = np.array([0, 0, 0])
    pages = np.array([1, 1, 2])
    readings = [["a", "b"], ["a", "a"], ["a", "a"]]
    h = scoring.loo_cluster_entropy(clusters, readings, pages)
    assert list(h) == [0.0, 0.0, pytest.approx(0.8112781244591328)]


def test_attrition_beyond_a_quarter_voids_the_gate():
    assert not scoring.void_for_attrition(kept=30, total=40)
    assert scoring.void_for_attrition(kept=29, total=40)


def test_glyph_width_alone_is_caught_by_the_within_type_width_baseline():
    rng, pages, tokens = _glyphs()
    width = rng.integers(2, 12, pages.size).astype(float)
    disagree = rng.random(pages.size) < 0.05 + 0.04 * width
    confidence = np.clip(0.95 - 0.02 * width + rng.normal(0, 0.01, pages.size), 0, 1)
    conf_wt = _ci(scoring.within_type_auroc(1 - confidence, disagree, tokens), pages)
    width_wt = scoring.within_type_auroc(width, disagree, tokens)(np.arange(pages.size))
    wp = _ci(scoring.within_page_auroc(1 - confidence, disagree, pages), pages)
    assert conf_wt.lo > 0.5
    assert scoring.decide_recognizer(conf_wt, conf_wt, wp, width_wt) == "kill"


def test_coverage_is_the_share_of_glyphs_in_scorable_groups():
    disagree = np.array([1] * 20 + [0] * 20 + [1] * 5 + [0] * 15, dtype=bool)
    tokens = np.array([0] * 40 + [1] * 20)
    assert scoring.within_type_coverage(disagree, tokens) == pytest.approx(40 / 60)


def test_underpower_voids_and_an_unset_threshold_refuses_to_decide():
    assert scoring.void_for_underpower(0.3, minimum=0.5)
    assert not scoring.void_for_underpower(0.6, minimum=0.5)
    with pytest.raises(RuntimeError):
        scoring.void_for_underpower(0.6, minimum=None)


GOOD, WEAK = Interval(0.62, 0.56, 0.68), Interval(0.52, 0.47, 0.57)


@pytest.mark.parametrize(
    ("wt_full", "wt_loo", "wp_full", "baseline", "verdict"),
    [
        (GOOD, GOOD, GOOD, 0.53, "pass"),
        (GOOD, WEAK, GOOD, 0.53, "narrow"),
        (GOOD, GOOD, WEAK, 0.53, "kill"),
        (GOOD, GOOD, GOOD, 0.58, "kill"),
        (WEAK, GOOD, GOOD, 0.40, "kill"),
    ],
)
def test_recognizer_gate_rule(wt_full, wt_loo, wp_full, baseline, verdict):
    assert scoring.decide_recognizer(wt_full, wt_loo, wp_full, baseline) == verdict
