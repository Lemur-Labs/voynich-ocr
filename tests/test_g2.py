from types import SimpleNamespace as C

import numpy as np
import pytest

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


def test_arm_without_a_token_holding_both_classes_has_no_estimate():
    metas = [{**m, "class": "agree"} for m in _metas(120)]
    x = np.random.default_rng(1).standard_normal((120, 8)).astype(np.float32)
    assert "gap" not in g2._arm(x, x, metas, 4)


def test_gate_refuses_a_second_run(tmp_path, monkeypatch):
    monkeypatch.setattr(g2, "OUT", tmp_path)
    monkeypatch.setattr(g2.freeze, "require", lambda *a: None)
    monkeypatch.setattr(g2, "run", lambda *a: pytest.fail("ran"))
    (tmp_path / "result.json").write_text("{}")
    with pytest.raises(SystemExit):
        g2.main(["m.safetensors", "--gate"])


def test_a_gate_run_that_crashes_still_counts_as_the_run(tmp_path, monkeypatch):
    monkeypatch.setattr(g2, "OUT", tmp_path / "g2")
    monkeypatch.setattr(g2.freeze, "require", lambda *a: None)

    def crash(*a):
        raise RuntimeError("mid-run")

    monkeypatch.setattr(g2, "run", crash)
    with pytest.raises(RuntimeError):
        g2.main(["m.safetensors", "--gate"])
    with pytest.raises(SystemExit):
        g2.main(["m.safetensors", "--gate"])


def test_load_refuses_features_that_do_not_line_up_with_instances(tmp_path, monkeypatch):
    monkeypatch.setattr(g2, "INSTANCES", tmp_path / "instances")
    monkeypatch.setattr(g2.clusters, "OUT", tmp_path / "clusters")
    (tmp_path / "instances").mkdir()
    (tmp_path / "clusters" / "features").mkdir(parents=True)
    (tmp_path / "instances" / "f1r.json").write_text('{"instances": [{"page": "f1r"}, {"page": "f1r"}]}')
    np.savez(tmp_path / "clusters" / "features" / "f1r.npz", dinov2=np.zeros((3, 4)), hog=np.zeros((3, 5)))
    with pytest.raises(AssertionError):
        g2._load(["f1r"])


def test_load_of_pages_without_instances_is_empty_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(g2, "INSTANCES", tmp_path)
    metas, feats = g2._load(["f1r"])
    assert metas == [] and len(feats["dinov2"]) == 0
