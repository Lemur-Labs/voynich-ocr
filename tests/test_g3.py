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
                    "class": "disagree" if disagree else "agree", "gated": True, "majority": ("o0",)})  # fmt: skip
    return out


def test_statistics_pass_when_confidence_separates_disputed_glyphs_within_type_and_page():
    maps = {name: _metas(600, signal=0.4) for name in g3.MAPS}
    out = g3.statistics(maps, {"o0": 0.3}, 0.3, {"o0": 1.0, "d0": 2.0})
    assert out["within_type"]["full"]["lo"] > 0.5 and out["within_page"]["lo"] > 0.5
    assert set(out["baselines"]["B1"]) == {"pooled"} and "within_type" in out["baselines"]["B4"]
    assert out["outcome_by_rule"] == "pass"


def _directional(n: int = 1200, pages: int = 12, seed: int = 1) -> list[dict]:
    """Disputed glyphs are narrow (B4 points down) and sit on low-confidence pages (B5 points down, weaker)."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        page = i % pages
        disagree = rng.random() < (0.45 if page < pages // 2 else 0.15)
        frames = rng.integers(1, 3) if disagree else rng.integers(2, 7)
        out.append({"page": f"f{page}r", "locus": f"f{page}r.1", "column": i, "token": ["o0", "d0"][i % 2],
                    "confidence": float(rng.uniform(0.3, 1.0)), "frames": int(frames),
                    "page_confidence": 0.6 if page < pages // 2 else 0.9,
                    "class": "disagree" if disagree else "agree", "gated": True, "majority": ("o0",)})  # fmt: skip
    return out


def test_baseline_bar_takes_the_larger_of_both_directions_of_span_width_and_page_confidence():
    maps = {name: _directional() for name in g3.MAPS}
    out = g3.statistics(maps, {}, 0.3, {"o0": 1.0, "d0": 2.0})
    b4, b5 = out["baselines"]["B4"]["within_type"], out["baselines"]["B5"]["within_type"]
    assert b4["higher"]["point"] < 0.3 and b4["lower"]["point"] > 0.7
    assert 0.5 < b5["lower"]["point"] < b4["lower"]["point"] and b5["higher"]["point"] < 0.5
    assert b4["lower"]["point"] == pytest.approx(1 - b4["higher"]["point"])
    assert out["baseline_bar"] == b4["lower"]["point"]


def test_each_map_is_scored_on_its_own_glyphs():
    maps = {"full": _metas(600, signal=0.4), "leave-ZL-out": _metas(600, signal=0.0, seed=1),
            "leave-ZL-IT-out": _metas(600, signal=-0.4, seed=2)}  # fmt: skip
    wt = g3.statistics(maps, {}, 0.3, {"o0": 1.0, "d0": 2.0})["within_type"]
    assert wt["full"]["point"] > 0.65 and abs(wt["leave-ZL-out"]["point"] - 0.5) < 0.1
    assert wt["leave-ZL-IT-out"]["point"] < 0.35


def test_ece_scores_agreement_with_the_leave_zl_it_out_majority():
    maps = {name: _metas(300) for name in g3.MAPS}
    for m in maps["leave-ZL-IT-out"]:
        m["confidence"], m["majority"] = 1.0, (m["token"],)
    assert g3.statistics(maps, {}, 0.3, {"o0": 1.0, "d0": 1.0})["ece"] == pytest.approx(0.0)


def test_a_glyph_in_a_merged_run_of_its_own_token_agrees_with_the_majority():
    maps = {name: _metas(300) for name in g3.MAPS}
    for m in maps["leave-ZL-IT-out"]:
        m["confidence"], m["majority"] = 1.0, (m["token"], m["token"])
    assert g3.statistics(maps, {}, 0.3, {"o0": 1.0, "d0": 1.0})["ece"] == pytest.approx(0.0)


def test_underpowered_coverage_voids_before_any_statistic(monkeypatch):
    metas = _metas(60)
    monkeypatch.setattr(g3.g2, "attrition", lambda *a: {"void": False})
    monkeypatch.setattr(g3, "statistics", lambda *a: pytest.fail("scored"))
    out = g3.decide({name: metas for name in g3.MAPS}, ["f1r"], None, {}, 0.3, {})
    assert out["outcome"] == "void" and out["coverage"]["within_type"] < g3.scoring.MIN_GROUP_COVERAGE


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
    model = tmp_path / "m.safetensors"
    model.write_bytes(b"weights")
    other = tmp_path / "other.safetensors"
    other.write_bytes(b"other weights")
    (tmp_path / "temperature.json").write_text(json.dumps(g3.temperature_record({"temperature": 1.5}, other)))
    with pytest.raises(SystemExit, match="model"):
        g3.main([str(model), "--gate"])


def test_gate_accepts_a_temperature_fitted_for_the_same_weights_at_another_path(tmp_path, monkeypatch):
    monkeypatch.setattr(g3, "OUT", tmp_path / "g3")
    monkeypatch.setattr(g3, "TEMPERATURE", tmp_path / "temperature.json")
    monkeypatch.setattr(g3.freeze, "require", lambda *a: None)
    monkeypatch.setattr(g3, "run", lambda *a: {"outcome": "kill"})
    (tmp_path / "a.safetensors").write_bytes(b"weights")
    (tmp_path / "b.safetensors").write_bytes(b"weights")
    record = g3.temperature_record({"temperature": 1.5}, tmp_path / "a.safetensors")
    (tmp_path / "temperature.json").write_text(json.dumps(record))
    g3.main([str(tmp_path / "b.safetensors"), "--gate"])
    assert json.loads((tmp_path / "g3" / "result.json").read_text())["outcome"] == "kill"


def test_gate_refuses_an_instance_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(g3, "OUT", tmp_path / "g3")
    monkeypatch.setattr(g3.freeze, "require", lambda *a: None)
    monkeypatch.setattr(g3, "run", lambda *a: pytest.fail("ran"))
    with pytest.raises(SystemExit, match="instances"):
        g3.main(["m.safetensors", "--gate", "--instances", str(tmp_path)])
    assert not (tmp_path / "g3").exists()


def test_a_dry_run_writes_under_build_and_never_results(tmp_path, monkeypatch):
    monkeypatch.setattr(g3, "ROOT", tmp_path)
    monkeypatch.setattr(g3, "OUT", tmp_path / "results" / "g3")
    monkeypatch.setattr(g3, "run", lambda *a: {"outcome": "void"})
    g3.main(["m.safetensors"])
    assert (tmp_path / "build" / "g3-dry" / "result.json").exists()
    assert not (tmp_path / "results").exists()


def test_once_the_gate_has_run_a_dry_run_reuses_the_temperature_and_never_refits(tmp_path, monkeypatch):
    monkeypatch.setattr(g3, "OUT", tmp_path / "g3")
    monkeypatch.setattr(g3, "TEMPERATURE", tmp_path / "temperature.json")
    (tmp_path / "g3").mkdir()
    (tmp_path / "g3" / "result.json").write_text("{}")
    (tmp_path / "temperature.json").write_text('{"temperature": 1.5}')
    assert g3.temperature(False, lambda: pytest.fail("refit"), tmp_path / "m.safetensors") == 1.5
    assert (tmp_path / "temperature.json").read_text() == '{"temperature": 1.5}'


def test_a_dry_run_before_the_gate_fits_and_records_the_model_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(g3, "OUT", tmp_path / "g3")
    monkeypatch.setattr(g3, "TEMPERATURE", tmp_path / "build" / "temperature.json")
    (tmp_path / "m.safetensors").write_bytes(b"weights")
    assert g3.temperature(False, lambda: {"temperature": 2.0}, tmp_path / "m.safetensors") == 2.0
    record = json.loads((tmp_path / "build" / "temperature.json").read_text())
    assert record["model_sha256"] == g3.sha256(tmp_path / "m.safetensors")


def test_b1_reads_non_test_pages_other_than_the_scored_ones(tmp_path):
    for page in ("f1r", "f2r", "f9r"):
        (tmp_path / f"{page}.json").write_text("{}")
    assert g3.b1_pages(tmp_path, test={"f9r"}, scored=["f2r"]) == ["f1r"]


def test_the_fit_skips_lines_whose_zl_label_has_a_question_mark():
    from voynich_ocr import disagreement as d
    from voynich_ocr.sta import Glyph

    aaa = {"A1": "o0", "B1": "d0"}
    zl = {"f1r.1": [Glyph("A1", False, ""), Glyph("B1", False, "")],
          "f1r.2": [Glyph("A1", False, ""), Glyph("Z1", False, "")]}  # fmt: skip
    inputs = d.Inputs({"ZL": d.Source(zl, frozenset(aaa))}, [], aaa)
    codec = type("Codec", (), {"encode": staticmethod(lambda s: np.array([{"a": 1, "b": 2}[c] for c in s]))})
    reads = {"f1r": {"pairs": {"f1r.1": 0, "f1r.2": 1},
                     "posteriors": {0: _posterior([0, 1, 0, 2]), 1: _posterior([0, 1, 0, 2])}}}  # fmt: skip
    fit = g3.fit_from(reads, inputs, {"o0": "a", "d0": "b"}, codec)
    assert fit["lines"] == 1 and fit["unlabelled"] == 1


def test_a_gate_run_that_crashes_still_counts_as_the_run(tmp_path, monkeypatch):
    monkeypatch.setattr(g3, "OUT", tmp_path / "g3")
    monkeypatch.setattr(g3, "TEMPERATURE", tmp_path / "temperature.json")
    monkeypatch.setattr(g3.freeze, "require", lambda *a: None)
    (tmp_path / "m.safetensors").write_bytes(b"weights")
    record = g3.temperature_record({"temperature": 1.5}, tmp_path / "m.safetensors")
    (tmp_path / "temperature.json").write_text(json.dumps(record))
    model = str(tmp_path / "m.safetensors")

    def crash(*a):
        raise RuntimeError("mid-run")

    monkeypatch.setattr(g3, "run", crash)
    with pytest.raises(RuntimeError):
        g3.main([model, "--gate"])
    with pytest.raises(SystemExit):
        g3.main([model, "--gate"])


def test_a_dry_run_on_other_pairs_fits_temperature_without_storing_it(monkeypatch, tmp_path):
    monkeypatch.setattr(g3, "OUT", tmp_path / "results")
    monkeypatch.setattr(g3, "TEMPERATURE", tmp_path / "temperature.json")
    (tmp_path / "m").write_bytes(b"weights")
    t = g3.temperature(False, lambda: {"temperature": 1.5}, tmp_path / "m", store=False)
    assert t == 1.5 and not (tmp_path / "temperature.json").exists()


def _stub_run(tmp_path, monkeypatch, read_pages, b1_pages):
    split = {"test": ["t1"], "validation": ["v1"]}
    (tmp_path / "splits.json").write_text(json.dumps(split))
    inst = tmp_path / "inst"
    inst.mkdir()
    for page in ("t1", "v1", "n1"):
        (inst / f"{page}.json").write_text("{}")
    (tmp_path / "lines").mkdir()
    (tmp_path / "lines" / "codec.json").write_text("{}")
    model = tmp_path / "m.safetensors"
    model.write_bytes(b"weights")
    monkeypatch.setattr(g3.d, "SPLITS", tmp_path / "splits.json")
    monkeypatch.setattr(g3.d, "load", lambda: type("Inputs", (), {"loci": []})())
    monkeypatch.setattr(g3.lines, "paragraph_loci", dict)
    monkeypatch.setattr(g3.lines, "OUT", tmp_path / "lines")
    monkeypatch.setattr(g3.recognize, "load", lambda p: type("M", (), {"net": type("N", (), {"codec": type("C", (), {"l2c": {}})})})())
    monkeypatch.setattr(g3, "read", lambda m, p, ids, i: read_pages.append(p) or {"pairs": {}, "blind": {}})
    monkeypatch.setattr(g3, "disagreement_rates", lambda i, b1: b1_pages.append(b1) or ({}, 0.3))
    monkeypatch.setattr(g3, "surprisal", lambda *a: {})
    monkeypatch.setattr(g3, "_evaluate", lambda *a: {"by_map": {"full": []}, "inserted": {}, "cer": {}, "lines": 0})
    monkeypatch.setattr(g3, "decide", lambda *a: {"outcome": "void"})
    monkeypatch.setattr(g3, "coverage", lambda metas: {})
    monkeypatch.setattr(g3, "TEMPERATURE", tmp_path / "gate" / "temperature.json")
    monkeypatch.setattr(g3, "OUT", tmp_path / "results" / "g3")
    return model, inst


def test_a_fit_for_a_reported_run_reads_validation_pages_and_stores_t_in_its_own_directory(tmp_path, monkeypatch):
    pages, b1 = [], []
    model, inst = _stub_run(tmp_path, monkeypatch, pages, b1)
    monkeypatch.setattr(g3, "fit_from", lambda *a: {"temperature": 1.5})
    (tmp_path / "seed").mkdir()
    out = g3.run(model, False, inst, None, tmp_path / "seed")
    assert pages == ["v1"] and out["temperature"] == 1.5 and b1 == [["n1"]]
    record = json.loads((tmp_path / "seed" / "temperature.json").read_text())
    assert record["model_sha256"] == g3.sha256(model) and record["instances_sha256"] == g3.instances_digest(inst)
    assert not (tmp_path / "gate").exists()


def test_a_reported_run_reads_test_pages_with_its_own_stored_t_and_never_fits(tmp_path, monkeypatch):
    pages, b1 = [], []
    model, inst = _stub_run(tmp_path, monkeypatch, pages, b1)
    monkeypatch.setattr(g3, "fit_from", lambda *a: pytest.fail("fitted on test pages"))
    (tmp_path / "seed").mkdir()
    (tmp_path / "seed" / "temperature.json").write_text(json.dumps(g3.temperature_record({"temperature": 1.5}, model)))
    out = g3.run(model, False, inst, tmp_path / "seed", None)
    assert pages == ["t1"] and out["temperature"] == 1.5 and out["eval"].startswith("test, reported only")
    assert b1 == [["n1", "v1"]]


def _fitted(seed, model, inst):
    seed.mkdir(parents=True, exist_ok=True)
    (seed / "validation").mkdir(exist_ok=True)
    (seed / "validation" / "result.json").write_text("{}")
    record = {**g3.temperature_record({"temperature": 1.5}, model),
              "instances": str(inst.resolve()), "instances_sha256": g3.instances_digest(inst)}  # fmt: skip
    (seed / "temperature.json").write_text(json.dumps(record))


@pytest.fixture
def report_root(tmp_path, monkeypatch):
    monkeypatch.setattr(g3, "ROOT", tmp_path)
    monkeypatch.setattr(g3, "OUT", tmp_path / "results" / "g3")
    monkeypatch.setattr(g3.freeze, "require", lambda *a: None)
    monkeypatch.setattr(g3, "run", lambda *a: pytest.fail("ran"))
    (tmp_path / "m.safetensors").write_bytes(b"weights")
    inst = tmp_path / "build" / "seed-instances"
    inst.mkdir(parents=True)
    (inst / "f1r.json").write_text("{}")
    return tmp_path, tmp_path / "m.safetensors", inst


@pytest.mark.parametrize("flag", ["--report", "--fit"])
@pytest.mark.parametrize("where", ["results/g3/seed", "results", "build/instances", "build/g3"])
def test_reported_runs_and_their_fits_refuse_directories_outside_build_or_inside_frozen_outputs(flag, where, report_root):
    root, model, inst = report_root
    with pytest.raises(SystemExit, match="build|frozen"):
        g3.main([str(model), flag, str(root / where), "--instances", str(inst)])
    assert not (root / "results").exists()


@pytest.mark.parametrize("flag", ["--report", "--fit"])
def test_reported_runs_and_their_fits_need_the_seeds_own_instances(flag, report_root):
    root, model, _ = report_root
    with pytest.raises(SystemExit, match="--instances"):
        g3.main([str(model), flag, str(root / "build" / "seed")])


@pytest.mark.parametrize("flags", [["--gate", "--report", "x"], ["--gate", "--fit", "x"], ["--fit", "x", "--report", "y"]])
def test_gate_report_and_fit_are_exclusive(flags, monkeypatch):
    monkeypatch.setattr(g3, "run", lambda *a: pytest.fail("ran"))
    with pytest.raises(SystemExit, match="exclusive"):
        g3.main(["m.safetensors", *flags])


def test_a_reported_run_refuses_to_start_without_its_own_fitted_temperature(report_root):
    root, model, inst = report_root
    with pytest.raises(SystemExit, match="--fit"):
        g3.main([str(model), "--report", str(root / "build" / "seed"), "--instances", str(inst)])
    assert not (root / "build" / "seed" / "result.json").exists()


def test_a_reported_run_refuses_a_temperature_fitted_for_another_model(report_root):
    root, model, inst = report_root
    (root / "other.safetensors").write_bytes(b"other weights")
    _fitted(root / "build" / "seed", root / "other.safetensors", inst)
    with pytest.raises(SystemExit, match="model"):
        g3.main([str(model), "--report", str(root / "build" / "seed"), "--instances", str(inst)])


def test_a_reported_run_refuses_a_temperature_without_its_validation_run(report_root):
    root, model, inst = report_root
    _fitted(root / "build" / "seed", model, inst)
    (root / "build" / "seed" / "validation" / "result.json").unlink()
    with pytest.raises(SystemExit, match="validation"):
        g3.main([str(model), "--report", str(root / "build" / "seed"), "--instances", str(inst)])


def test_a_reported_run_refuses_instances_that_changed_since_the_fit(report_root):
    root, model, inst = report_root
    _fitted(root / "build" / "seed", model, inst)
    (inst / "f2r.json").write_text("{}")
    with pytest.raises(SystemExit, match="instances"):
        g3.main([str(model), "--report", str(root / "build" / "seed"), "--instances", str(inst)])


def test_a_reported_run_checks_the_config_hash_before_it_starts(report_root, monkeypatch):
    root, model, inst = report_root
    _fitted(root / "build" / "seed", model, inst)

    def unrecorded(*a):
        raise SystemExit("config hash not recorded")

    monkeypatch.setattr(g3.freeze, "require", unrecorded)
    with pytest.raises(SystemExit, match="hash"):
        g3.main([str(model), "--report", str(root / "build" / "seed"), "--instances", str(inst)])
    assert not (root / "build" / "seed" / "result.json").exists()


def test_a_reported_run_writes_once_into_its_directory_and_never_writes_results(report_root, monkeypatch):
    root, model, inst = report_root
    _fitted(root / "build" / "seed", model, inst)
    monkeypatch.setattr(g3, "run", lambda *a: {"outcome": "pass"})
    argv = [str(model), "--report", str(root / "build" / "seed"), "--instances", str(inst)]
    g3.main(argv)
    assert json.loads((root / "build" / "seed" / "result.json").read_text())["outcome"] == "pass"
    assert not (root / "results").exists()
    with pytest.raises(FileExistsError):
        g3.main(argv)


def test_a_fit_refuses_to_overwrite_a_fitted_temperature(report_root):
    root, model, inst = report_root
    _fitted(root / "build" / "seed", model, inst)
    with pytest.raises(SystemExit, match="fitted"):
        g3.main([str(model), "--fit", str(root / "build" / "seed"), "--instances", str(inst)])
