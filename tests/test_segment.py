from voynich_ocr import segment as sg


def _line(x0, x1, y0, y1=None):
    y1 = y0 if y1 is None else y1
    return {"baseline": [[x0, y0], [x1, y1]], "boundary": [[x0, y0 - 30], [x1, y1 - 30], [x1, y1 + 5], [x0, y0 + 5]]}


def test_fragments_of_one_row_merge_left_to_right():
    lines = [_line(1200, 2000, 105), _line(100, 1100, 100), _line(100, 2000, 200), _line(100, 2000, 300)]
    rows = sg.page_lines(lines, 1000)
    assert [r["baseline"][0] for r in rows] == [[100, 100], [100, 200], [100, 300]]
    assert rows[0]["baseline"][-1] == [2000, 105]


def test_lines_in_the_top_band_are_dropped():
    rows = sg.page_lines([_line(1500, 2200, 150), _line(100, 2000, 400), _line(100, 2000, 500)], 4000)
    assert [r["baseline"][0][1] for r in rows] == [400, 500]


def test_lines_on_neighbouring_rows_do_not_merge():
    lines = [_line(100, 1100, 100), _line(1200, 2000, 160), _line(100, 2000, 210)]
    assert len(sg.page_lines(lines, 1000)) == 3


def test_short_lines_are_dropped_and_rows_read_top_to_bottom():
    lines = [_line(100, 2000, 300), _line(100, 160, 250), _line(100, 2000, 100), _line(100, 900, 200)]
    rows = sg.page_lines(lines, 1000)
    assert [r["baseline"][0][1] for r in rows] == [100, 200, 300]


def test_rows_pair_with_loci_only_when_the_counts_match():
    rows = sg.page_lines([_line(100, 2000, 300), _line(100, 2000, 400)], 4000)
    assert sg.assign(rows, ["f1r.1", "f1r.2"]) == {"f1r.1": rows[0], "f1r.2": rows[1]}
    assert sg.assign(rows, ["f1r.1", "f1r.2", "f1r.3"]) is None


def test_merged_baseline_never_runs_backwards():
    rows = sg.page_lines([_line(100, 1100, 100), _line(1080, 2000, 102), _line(100, 2000, 200)], 1000)
    xs = [p[0] for p in rows[0]["baseline"]]
    assert xs == sorted(xs)
