from types import SimpleNamespace as C

import numpy as np

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


def _metas(n, pages=6):
    rng = np.random.default_rng(0)
    return [
        {"page": f"f{i % pages}r", "class": "disagree" if rng.random() < 0.3 else "agree", "zl": "o0",
         "gated": True, "readings": {"ZL": "o0", "IT": "o0" if rng.random() < 0.7 else "a0", "GC": "o0"}}
        for i in range(n)
    ]  # fmt: skip


def test_arm_scores_float32_features():
    x = np.random.default_rng(1).standard_normal((120, 8)).astype(np.float32)
    out = g2._arm(x, x, _metas(120), 4)
    assert "gap" in out
