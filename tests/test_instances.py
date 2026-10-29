from voynich_ocr import instances as ins

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
