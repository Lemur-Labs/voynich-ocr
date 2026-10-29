import json

import pytest

from voynich_ocr import freeze


def _root(tmp_path):
    for rel in ("docs/prereg/splits.json", "snapshot/manifest.sha256", "uv.lock", "build/lines/train.txt",
                "build/seg/f1r.json", "build/seg/f9r.json", "build/instances/f1r.json",
                "build/clusters/features/f1r.npz"):  # fmt: skip
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x")
    (tmp_path / "docs/prereg/splits.json").write_text(json.dumps({"test": ["f9r"]}))
    model = tmp_path / "m.safetensors"
    model.write_bytes(b"weights")
    return model


def test_test_inference_refuses_until_the_config_hash_is_recorded(tmp_path):
    model = _root(tmp_path)
    decisions = tmp_path / "decisions.yaml"
    decisions.write_text("- id: VO-001\n")
    with pytest.raises(SystemExit):
        freeze.require(model, decisions, tmp_path)
    decisions.write_text(f"- decision: config {freeze.config_hash(model, tmp_path)}\n")
    freeze.require(model, decisions, tmp_path)


def test_hash_follows_fit_page_outputs_and_line_labels_but_not_test_page_outputs(tmp_path):
    model = _root(tmp_path)
    before = freeze.config_hash(model, tmp_path)
    (tmp_path / "build/seg/f9r.json").write_text("test page segmented later")
    assert freeze.config_hash(model, tmp_path) == before
    (tmp_path / "build/lines/f1r_1.gt.txt").write_text("label")
    assert freeze.config_hash(model, tmp_path) != before
    after = freeze.config_hash(model, tmp_path)
    (tmp_path / "build/instances/f1r.json").write_text("y")
    assert freeze.config_hash(model, tmp_path) != after
