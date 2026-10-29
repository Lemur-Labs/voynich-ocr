import numpy as np

from voynich_ocr import recognize as rc


def _probs(frames: list[int], classes: int = 4, p: float = 0.7) -> np.ndarray:
    out = np.full((classes, len(frames)), (1 - p) / (classes - 1))
    for t, c in enumerate(frames):
        out[c, t] = p
    return out


def test_spans_are_maximal_argmax_runs_of_non_blank_classes():
    probs = _probs([0, 2, 2, 0, 2, 3, 3, 0])
    probs[2, 2] = 0.9
    assert rc.spans(probs) == [(2, 1, 3, 0.9), (2, 4, 5, 0.7), (3, 5, 7, 0.7)]


def test_text_assignment_skips_spurious_rows_and_keeps_order():
    loci = {"f1r.1": ["a", "b", "c"], "f1r.2": ["d", "e", "f"]}
    rows = [["x", "y"], ["a", "b", "c"], ["q"], ["d", "e", "g"]]
    assert rc.assign_by_text(rows, loci) == {"f1r.1": 1, "f1r.2": 3}


def test_text_assignment_leaves_a_locus_unmatched_when_no_row_resembles_it():
    loci = {"f1r.1": ["a", "b"], "f1r.2": ["d", "e"]}
    assert rc.assign_by_text([["a", "b"], ["x", "y"]], loci) == {"f1r.1": 0}


def test_consensus_drops_gap_majorities_and_breaks_ties_in_source_order():
    readings = [
        {"ZL": ("a",), "IT": ("a",), "GC": ("o",)},
        {"ZL": (), "IT": (), "GC": ("e",)},
        {"ZL": ("d",), "IT": ("s",), "GC": ()},
    ]
    assert rc.consensus(readings) == [("a", 0), ("d", 2)]


def test_recognized_glyphs_inherit_columns_and_insertions_are_counted():
    cons = [("a", 0), ("b", 1), ("c", 2)]
    columns, inserted = rc.align_to_columns(["a", "x", "b", "d"], cons)
    assert columns == [0, None, 1, 2]
    assert inserted == 1


def test_regions_split_the_gaps_between_neighbouring_spans_at_their_midpoints():
    runs = [(1, 10, 12, 0.9), (2, 20, 22, 0.9), (1, 40, 41, 0.9)]
    assert rc.regions(runs, 48) == [(6.0, 16.0), (16.0, 31.0), (31.0, 48)]


def test_a_lone_span_keeps_its_own_frames():
    assert rc.regions([(1, 5, 7, 0.9)], 30) == [(5, 7)]


def test_frame_to_baseline_map_fits_kraken_cuts_with_inclusive_ends_and_skips_clamped_points():
    runs = [(1, 0, 2, 0.9), (2, 7, 8, 0.9), (1, 12, 14, 0.9), (2, 20, 21, 0.9)]
    cuts = [[0, 0], [50, 50], [100, 110], [180, 180]]
    a, b = rc.baseline_map(runs, cuts)
    assert abs(a - 10) < 1e-9 and abs(b + 20) < 1e-9


def test_frame_to_baseline_map_needs_two_unclamped_frames():
    assert rc.baseline_map([(1, 0, 1, 0.9), (2, 9, 10, 0.9)], [[0, 0], [70, 70]]) is None


def test_rescaled_posteriors_equal_a_softmax_of_the_raw_logits_divided_by_the_temperature():
    raw = np.random.default_rng(0).standard_normal((5, 9)) * 4
    probs = np.exp(raw) / np.exp(raw).sum(axis=0)
    hot = np.exp(raw / 2.5) / np.exp(raw / 2.5).sum(axis=0)
    assert np.allclose(np.exp(rc.log_posteriors(probs, 2.5)), hot)


def test_rescaling_keeps_every_frame_argmax_so_spans_keep_their_frames():
    probs = _probs([0, 2, 2, 0, 2, 3, 3, 0])
    hot = np.exp(rc.log_posteriors(probs, 3.0))
    assert [s[:3] for s in rc.spans(hot)] == [s[:3] for s in rc.spans(probs)]
