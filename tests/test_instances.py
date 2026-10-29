from voynich_ocr import disagreement as d
from voynich_ocr import instances as ins
from voynich_ocr.sta import Glyph

IDS = [f"f1r.{i}" for i in range(1, 7)]
ZL = {k: ["o0"] * n for k, n in zip(IDS, [10, 20, 30, 40, 50, 60], strict=True)}
LABELS = {k: [*v, " ", "o0"] for k, v in ZL.items()}
ROWS = [["o0"] * n for n in [10, 20, 30, 40, 50, 60]]


def test_tall_row_is_dropped_after_counting_so_later_rows_keep_their_loci():
    sizes = [(100, 10), (200, 10), (300, 30), (400, 10), (500, 10), (600, 10)]
    pairs, rule = ins.pair_rows(sizes, IDS, LABELS, ZL, ROWS)
    assert rule == "count"
    assert pairs == {"f1r.1": 0, "f1r.2": 1, "f1r.4": 3, "f1r.5": 4, "f1r.6": 5}


def test_counts_that_match_but_widths_that_do_not_track_lengths_fall_back_to_text():
    sizes = [(600, 10), (500, 10), (400, 10), (300, 10), (200, 10), (100, 10)]
    _, rule = ins.pair_rows(sizes, IDS, LABELS, ZL, ROWS)
    assert rule == "text"


def test_unlabelled_line_is_screened_out_of_the_width_check_but_kept_when_not_tall():
    sizes = [(100, 10), (200, 10), (900, 10), (400, 10), (500, 10), (600, 10)]
    pairs, rule = ins.pair_rows(sizes, IDS, {**LABELS, "f1r.3": None}, ZL, ROWS)
    assert rule == "count" and pairs["f1r.3"] == 2


def test_text_pairing_reports_original_row_indices():
    sizes = [(100, 10), (50, 40), (200, 10), (300, 10), (400, 10), (500, 10), (600, 10)]
    rows = [ROWS[0], ["o0"] * 3, *ROWS[1:]]
    pairs, rule = ins.pair_rows(sizes, IDS, LABELS, ZL, rows)
    assert rule == "text"
    assert pairs == {"f1r.1": 0, "f1r.2": 2, "f1r.3": 3, "f1r.4": 4, "f1r.5": 5, "f1r.6": 6}


def test_blind_pairing_uses_only_line_heights_and_the_locus_count():
    sizes = [(100, 10), (200, 10), (300, 30), (400, 10), (500, 10), (600, 10), (700, 10)]
    pairs, rule = ins.pair_rows_blind(sizes, IDS)
    assert rule == "blind"
    assert pairs == {"f1r.1": 0, "f1r.2": 1, "f1r.3": 3, "f1r.4": 4, "f1r.5": 5, "f1r.6": 6}


def test_blind_pairing_drops_a_page_whose_single_rows_do_not_match_its_loci():
    pairs, _ = ins.pair_rows_blind([(100, 10)] * 5, IDS)
    assert pairs == {}


def test_glyphs_take_columns_from_the_consensus_of_the_map_they_are_aligned_to():
    aaa = {"A1": "o0", "B1": "d0", "E1": "i0"}
    with_d, without_d = ["A1", "B1", "E1"], ["A1", "E1"]
    codes = {"ZL": with_d, "IT": with_d, "GC": with_d, "FG": without_d, "CD": without_d}
    sources = {s: d.Source({"f1r.1": [Glyph(c, False, "") for c in cs]}, frozenset(aaa)) for s, cs in codes.items()}
    inputs = d.Inputs(sources, [d.Locus("f1r.1", "f1r", {})], aaa)
    cols, where, inserted = ins.columns_for(inputs.loci[0], ["o0", "d0", "i0"], inputs, d.MAPS["full"])
    assert where == [0, 1, 2] and inserted == 0
    cols, where, inserted = ins.columns_for(inputs.loci[0], ["o0", "d0", "i0"], inputs, d.MAPS["leave-ZL-IT-out"])
    assert where == [0, None, 2] and inserted == 1
    assert cols[0].contributing == ("GC", "FG", "CD")
