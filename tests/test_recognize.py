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
