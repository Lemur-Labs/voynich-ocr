from types import SimpleNamespace as C

from voynich_ocr import g2


def test_readable_columns_are_gated_paragraph_columns_on_imaged_eval_pages():
    cols = [
        C(page="f1r", locus="f1r.1", index=0, gated=True),
        C(page="f1r", locus="f1r.1", index=1, gated=False),
        C(page="f1r", locus="f1r.L1", index=0, gated=True),
        C(page="f2r", locus="f2r.1", index=0, gated=True),
        C(page="f3r", locus="f3r.1", index=0, gated=True),
    ]
    paragraph = {"f1r": ["f1r.1"], "f2r": ["f2r.1"], "f3r": ["f3r.1"]}
    assert g2.readable(cols, ["f1r", "f2r"], {"f1r", "f3r"}, paragraph) == {("f1r.1", 0)}
