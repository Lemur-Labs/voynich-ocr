import pytest

from voynich_ocr import freeze


def test_test_inference_refuses_until_the_config_hash_is_recorded(tmp_path):
    model = tmp_path / "m.safetensors"
    model.write_bytes(b"weights")
    decisions = tmp_path / "decisions.yaml"
    decisions.write_text("- id: VO-001\n")
    with pytest.raises(SystemExit):
        freeze.require(model, decisions)
    decisions.write_text(f"- decision: config {freeze.config_hash(model)}\n")
    freeze.require(model, decisions)


def test_hash_covers_scoring_the_map_the_split_the_codec_the_features_and_the_lockfile():
    for path in ("src/voynich_ocr/scoring.py", "src/voynich_ocr/disagreement.py", "docs/prereg/splits.json",
                 "build/lines/codec.json", "uv.lock"):  # fmt: skip
        assert path in freeze.FROZEN
