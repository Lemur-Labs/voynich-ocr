import numpy as np
from PIL import Image

from voynich_ocr import proposer as pr


def test_components_are_ink_blobs_left_to_right_ignoring_specks():
    line = np.full((40, 120), 230, dtype=np.uint8)
    line[10:30, 70:90] = 10
    line[10:30, 10:25] = 10
    line[5, 50] = 10
    boxes = pr.components(Image.fromarray(line))
    assert boxes == [(10, 10, 25, 30), (70, 10, 90, 30)]


def test_black_fill_outside_the_line_polygon_is_not_ink():
    line = np.full((40, 120, 3), 230, dtype=np.uint8)
    line[:5] = 0
    line[-5:] = 0
    line[12:28, 10:25] = 40
    line[12:28, 70:90] = 40
    assert pr.components(Image.fromarray(line)) == [(10, 12, 25, 28), (70, 12, 90, 28)]


def test_paired_rows_index_the_unfiltered_page_rows():
    rows = [{"n": i} for i in range(5)]
    assert pr.paired_rows(rows, {"f1r.1": 0, "f1r.3": 4}) == [("f1r.1", {"n": 0}), ("f1r.3", {"n": 4})]
