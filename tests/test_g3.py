import json

import numpy as np
import pytest

from voynich_ocr import g3


def _posterior(path: list[int], classes: int = 4, sharpness: float = 4.0) -> np.ndarray:
    raw = np.zeros((classes, len(path)))
    raw[path, np.arange(len(path))] = sharpness
    return np.exp(raw) / np.exp(raw).sum(axis=0)


def test_stroke_count_is_the_number_of_aaa_strokes_in_the_token():
    assert [g3.strokes(t) for t in ["o0", "i2:j1", "c0~c0:t0~c0", "a2:i3:l3:x1:c3:c1"]] == [1, 2, 4, 6]


def test_a_recognizer_that_is_right_but_unsure_is_sharpened_by_the_fit():
    post = [_posterior([0, 1, 0, 2, 0, 3], sharpness=1.0)] * 3
    fit = g3.fit_temperature(post, [[1, 2, 3]] * 3)
    assert fit["temperature"] == g3.GRID[0]


def test_a_recognizer_that_is_confidently_wrong_is_softened_by_the_fit():
    post = [_posterior([0, 1, 0, 2, 0, 3], sharpness=8.0), _posterior([0, 1, 0, 2, 0, 1], sharpness=8.0)]
    fit = g3.fit_temperature(post, [[1, 2, 3], [1, 2, 3]])
    assert 1.0 < fit["temperature"] < g3.GRID[-1]
    assert min(fit["loss"].values()) == fit["loss"][str(fit["temperature"])]


def test_temperature_grid_runs_from_half_to_five_in_twentieths():
    assert len(g3.GRID) == 91 and g3.GRID[0] == 0.5 and g3.GRID[-1] == 5.0 and g3.GRID[1] == 0.55


def test_a_label_the_frames_cannot_hold_is_dropped_from_the_fit_and_counted():
    post = [_posterior([0, 1, 0, 2]), _posterior([1, 2])]
    fit = g3.fit_temperature(post, [[1, 2], [1, 2, 2, 1]])
    assert fit["lines"] == 1 and fit["dropped"] == 1


def test_glyph_confidence_is_the_peak_posterior_of_the_emitted_class_at_the_temperature():
    post = _posterior([0, 1, 1, 0, 2], sharpness=3.0)
    post[1, 2] = 0.95
    post[:, 2] /= post[:, 2].sum()
    cold, hot = g3.glyphs(post, 1.0, {(1,): "a", (2,): "b"}), g3.glyphs(post, 2.0, {(1,): "a", (2,): "b"})
    assert [(g["char"], g["frames"]) for g in hot] == [("a", 2), ("b", 1)]
    assert cold[0]["confidence"] == pytest.approx(post[1, 1:3].max())
    assert hot[0]["confidence"] < cold[0]["confidence"]


def test_b1_rates_are_per_recognized_token_over_gated_instances_and_unknown_tokens_fall_back_to_the_pool(tmp_path):
    rows = [("o0", "disagree", True), ("o0", "agree", True), ("o0", "disagree", False), ("d0", "agree", True)]
    (tmp_path / "f1r.json").write_text(json.dumps(
        {"instances": [{"token": t, "class": c, "gated": g} for t, c, g in rows]}))  # fmt: skip
    (tmp_path / "f9r.json").write_text("not read")
    rates, pooled = g3.disagreement_rates(tmp_path, ["f1r"])
    assert rates == {"o0": 0.5, "d0": 0.0} and pooled == pytest.approx(1 / 3)


def test_b2_surprisal_counts_tokens_in_the_training_labels_only(tmp_path, monkeypatch):
    monkeypatch.setattr(g3, "ROOT", tmp_path)
    (tmp_path / "train.txt").write_text("a.png\n")
    (tmp_path / "a.gt.txt").write_text("xx y\n")
    (tmp_path / "eval.txt").write_text("b.png\n")
    (tmp_path / "b.gt.txt").write_text("zzzz\n")
    out = g3.surprisal(tmp_path, {"x": "o0", "y": "d0", "z": "i0"})
    assert out == pytest.approx({"o0": -np.log(2 / 3), "d0": -np.log(1 / 3)})


def test_cer_is_total_edits_over_total_reference_length():
    assert g3.cer([(["a", "b"], ["a", "c", "d"]), (["x"], ["x"])]) == pytest.approx(2 / 4)


def _metas(n: int, pages: int = 12, signal: float = 0.0, seed: int = 0) -> list[dict]:
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        disagree = rng.random() < 0.3
        conf = float(np.clip(rng.uniform(0.3, 1.0) - signal * disagree, 0.01, 1.0))
        out.append({"page": f"f{i % pages}r", "locus": f"f{i % pages}r.1", "column": i, "token": ["o0", "d0"][i % 2],
                    "confidence": conf, "frames": int(rng.integers(1, 6)), "page_confidence": 0.8,
                    "class": "disagree" if disagree else "agree", "gated": True, "majority": "o0"})  # fmt: skip
    return out


def test_statistics_put_the_within_type_baseline_bar_at_the_larger_of_span_width_and_page_confidence():
    maps = {name: _metas(600, signal=0.4) for name in g3.MAPS}
    out = g3.statistics(maps, {"o0": 0.3}, 0.3, {"o0": 1.0, "d0": 2.0})
    bar = max(out["baselines"]["B4"]["within_type"]["point"], out["baselines"]["B5"]["within_type"]["point"])
    assert out["baseline_bar"] == bar
    assert out["within_type"]["full"]["lo"] > 0.5 and out["within_page"]["lo"] > 0.5
    assert set(out["baselines"]["B1"]) == {"pooled"} and "within_type" in out["baselines"]["B4"]
    assert out["outcome_by_rule"] == "pass"


def test_ece_scores_agreement_with_the_leave_zl_it_out_majority():
    maps = {name: _metas(300) for name in g3.MAPS}
    for m in maps["leave-ZL-IT-out"]:
        m["confidence"], m["majority"] = 1.0, m["token"]
    assert g3.statistics(maps, {}, 0.3, {"o0": 1.0, "d0": 1.0})["ece"] == pytest.approx(0.0)


def test_underpowered_coverage_voids_before_any_statistic(monkeypatch):
    metas = _metas(60)
    monkeypatch.setattr(g3.g2, "attrition", lambda *a: {"void": False})
    monkeypatch.setattr(g3, "statistics", lambda *a: pytest.fail("scored"))
    out = g3.decide({name: metas for name in g3.MAPS}, ["f1r"], None, {}, 0.3, {})
    assert out["outcome"] == "void" and out["coverage"]["within_type"] < 0.72


def test_attrition_voids_the_gate(monkeypatch):
    monkeypatch.setattr(g3.g2, "attrition", lambda *a: {"void": True})
    monkeypatch.setattr(g3, "statistics", lambda *a: pytest.fail("scored"))
    out = g3.decide({name: _metas(600) for name in g3.MAPS}, ["f1r"], None, {}, 0.3, {})
    assert out["outcome"] == "void"


def test_gate_refuses_a_second_run(tmp_path, monkeypatch):
    monkeypatch.setattr(g3, "OUT", tmp_path)
    monkeypatch.setattr(g3.freeze, "require", lambda *a: None)
    monkeypatch.setattr(g3, "run", lambda *a: pytest.fail("ran"))
    (tmp_path / "result.json").write_text("{}")
    with pytest.raises(SystemExit):
        g3.main(["m.safetensors", "--gate"])


def test_gate_refuses_to_start_without_a_fitted_temperature(tmp_path, monkeypatch):
    monkeypatch.setattr(g3, "OUT", tmp_path / "g3")
    monkeypatch.setattr(g3, "TEMPERATURE", tmp_path / "temperature.json")
    monkeypatch.setattr(g3.freeze, "require", lambda *a: None)
    monkeypatch.setattr(g3, "run", lambda *a: pytest.fail("ran"))
    with pytest.raises(SystemExit, match="temperature"):
        g3.main(["m.safetensors", "--gate"])
    assert not (tmp_path / "g3" / "result.json").exists()


def test_gate_refuses_a_temperature_fitted_for_another_model(tmp_path, monkeypatch):
    monkeypatch.setattr(g3, "OUT", tmp_path / "g3")
    monkeypatch.setattr(g3, "TEMPERATURE", tmp_path / "temperature.json")
    monkeypatch.setattr(g3.freeze, "require", lambda *a: None)
    monkeypatch.setattr(g3, "run", lambda *a: pytest.fail("ran"))
    (tmp_path / "temperature.json").write_text(json.dumps({"temperature": 1.5, "model": "other.safetensors"}))
    with pytest.raises(SystemExit, match="model"):
        g3.main(["m.safetensors", "--gate"])


def test_a_gate_run_that_crashes_still_counts_as_the_run(tmp_path, monkeypatch):
    monkeypatch.setattr(g3, "OUT", tmp_path / "g3")
    monkeypatch.setattr(g3, "TEMPERATURE", tmp_path / "temperature.json")
    monkeypatch.setattr(g3.freeze, "require", lambda *a: None)
    (tmp_path / "temperature.json").write_text(json.dumps({"temperature": 1.5, "model": "m.safetensors"}))

    def crash(*a):
        raise RuntimeError("mid-run")

    monkeypatch.setattr(g3, "run", crash)
    with pytest.raises(RuntimeError):
        g3.main(["m.safetensors", "--gate"])
    with pytest.raises(SystemExit):
        g3.main(["m.safetensors", "--gate"])
