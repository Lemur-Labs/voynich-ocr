import hashlib
import json

import numpy as np
import pytest

from voynich_ocr import h4

BOX = np.random.default_rng(0).integers(0, 256, (20, 30, 3), dtype=np.uint8)


def test_the_operator_is_byte_exact_at_each_degraded_level():
    digests = {lv: hashlib.sha256(h4.degrade(BOX, lv, u).tobytes()).hexdigest() for lv, u in [(1, 0.37), (2, 0.81)]}
    assert digests == {
        1: "e94cba5fda7bc0e3e498773d4d60f093359a6bed296b8b46ab462d3b4ca762dd",
        2: "16aad7f9e8866d801dd141c22bb61c693e9dc92a1209485d35b37adb3099706a",
    }


def test_level_zero_leaves_the_box_unchanged():
    assert np.array_equal(h4.degrade(BOX, 0, 0.5), BOX)


def test_the_band_is_the_background_at_the_drawn_offset():
    out = h4.degrade(BOX, 1, 0.37)
    b = np.rint(h4.background(BOX)).astype(np.uint8)
    w, left = round(0.2 * 30), int(np.floor(0.37 * (30 - 6 + 1)))
    assert (w, left) == (6, 9)
    assert (out[:, left : left + w] == b).all()
    assert not (out[:, left - 1] == b).all() and not (out[:, left + w] == b).all()


def test_a_blank_box_stays_blank_at_every_level():
    blank = np.full((12, 9, 3), 200, dtype=np.uint8)
    for level in range(3):
        assert np.array_equal(h4.degrade(blank, level, 0.5), blank)


def test_fade_moves_ink_toward_the_background_by_a():
    box = np.full((10, 40, 3), 200, dtype=np.uint8)
    box[4:6, 30:34] = 0
    out = h4.degrade(box, 2, 0.0).astype(float)
    assert out[:, :16].min() == 200
    assert out[4:6, 30:34].mean() > 200 * (1 - 0.35)


def test_collage_aligns_bottoms_with_margins_and_a_baseline_above_the_bottom_edge():
    tall = np.zeros((10, 4, 3), dtype=np.uint8)
    short = np.full((6, 3, 3), 50, dtype=np.uint8)
    image, baseline = h4.collage([[tall], [short]], [5], np.array([255.0, 255.0, 255.0]))
    a = np.asarray(image)
    assert a.shape == (10 + 16, 8 + 4 + 5 + 3 + 8, 3)
    assert (a[8:18, 8:12] == 0).all()
    assert (a[12:18, 17:20] == 50).all() and (a[8:12, 17:20] == 255).all()
    assert baseline == [[0, 26 - 8], [27, 26 - 8]]


def test_a_draw_takes_floor_of_u_times_n():
    assert [h4.draw(u, 3) for u in (0.0, 0.333, 0.334, 0.999)] == [0, 0, 1, 2]


def test_streams_are_the_seed_sequences_children_in_a7_order():
    rng = h4.streams()
    child = np.random.SeedSequence(h4.SEED).spawn(6)[h4.STREAMS.index("spacing")]
    assert rng["spacing"].random() == np.random.default_rng(child).random()


def _ex(i: int) -> h4.Exemplar:
    return h4.Exemplar("f1r", "f1r.1", i, i, ((0, 0), (1, 1)))


def _wex(i: int, n: int = 2) -> h4.WordExemplar:
    return h4.WordExemplar("f11r", "f11r.1", i, tuple(((10 * k, 0), (10 * k + 9, 0), (10 * k + 9, 5), (10 * k, 5))
                                                         for k in range(n)))  # fmt: skip


def _glyphs(p, name):
    return [g for w in p[name][0]["words"] for g in w["glyphs"]]


def test_a_glyph_with_no_pool_still_takes_its_draws_so_later_glyphs_keep_theirs():
    pools = {"a": [_ex(i) for i in range(50)]}
    with_gap = h4.plan([[["z", "a"]]], {}, pools, {}, [3])
    without = h4.plan([[["a", "a"]]], {}, pools, {}, [3])
    assert with_gap["gaps"] == 1
    assert _glyphs(with_gap, "R0")[-1]["exemplar"] == _glyphs(without, "R0")[-1]["exemplar"]
    assert _glyphs(with_gap, "R1")[-1]["level"] == _glyphs(without, "R1")[-1]["level"]


def test_a_word_draw_does_not_shift_the_glyph_streams():
    pools = {"a": [_ex(i) for i in range(50)], "b": [_ex(100 + i) for i in range(50)]}
    matched = h4.plan([[["a", "b"]]], {("a", "b"): [_wex(0)]}, pools, {}, [3])
    unmatched = h4.plan([[["a", "b"]]], {}, pools, {}, [3])
    assert [g["level"] for g in _glyphs(matched, "R1")] == [g["level"] for g in _glyphs(unmatched, "R1")]
    assert [g["arm"] for g in _glyphs(matched, "R1")] == ["matched", "matched"]
    assert [g["arm"] for g in _glyphs(unmatched, "R1")] == ["unmatched", "unmatched"]
    assert matched["R0"][0]["words"][0]["exemplar"] == _wex(0)


def test_a_matched_word_renders_even_when_a_glyph_has_no_glyph_exemplar_but_r2_counts_it_as_a_gap():
    p = h4.plan([[["z"]]], {("z",): [_wex(0, 1)]}, {}, {}, [3])
    assert p["gaps"] == 0 and p["R2_gaps"] == 1
    assert len(_glyphs(p, "R0")) == 1 and _glyphs(p, "R2") == []


def test_r2_uses_a_disputed_glyph_where_it_exists_and_gap_pool_spacing():
    pools = {"a": [_ex(i) for i in range(50)], "b": [_ex(100 + i) for i in range(50)]}
    p = h4.plan([[["a", "b"], ["a"]]], {("a", "b"): [_wex(0)]}, pools, {"a": [_ex(900)]}, [7])
    r2 = _glyphs(p, "R2")
    assert [g["disputed"] for g in r2] == [True, False, True]
    assert r2[0]["exemplar"] == _ex(900) and all(g["level"] == 0 for g in r2)
    assert p["R2"][0]["spaces"] == [7]


def test_word_regions_run_between_successive_cut_left_edges_clamped_into_the_crop():
    w = h4.WordExemplar("f11r", "f11r.1", 0, (((5, 0), (14, 0)), ((12, 0), (30, 0)), ((11, 0), (40, 0))))
    assert w.regions(36) == [(0, 7), (7, 7), (7, 36)]


def test_each_glyph_of_a_matched_word_is_degraded_in_its_own_region():
    crop = np.random.default_rng(3).integers(0, 256, (12, 20, 3), dtype=np.uint8)
    wex = h4.WordExemplar("f11r", "f11r.1", 0, (((0, 0), (9, 0)), ((10, 0), (19, 0))))
    line = {"words": [{"exemplar": wex, "glyphs": [{"level": 0, "u": 0.5}, {"level": 2, "u": 0.0}]}]}
    image, _ = h4.render(line, {wex.key: crop})
    a = np.asarray(image)[8:20, 8:28]
    assert np.array_equal(a[:, :10], crop[:, :10])
    assert np.array_equal(a[:, 10:], h4.degrade(crop[:, 10:], 2, 0.0))


def test_alignment_prefers_the_diagonal_then_deletion():
    assert h4.alignment(["a", "b"], ["a", "b"]) == [(0, 0), (1, 1)]
    assert h4.alignment(["a"], ["a", "b"]) == [(0, 0), (None, 1)]
    assert h4.alignment(["a", "x", "b"], ["a", "b"]) == [(0, 0), (1, None), (2, 1)]


def _rendered(spec):
    return [{"token": t, "level": lv, "arm": arm, "exemplar": _ex(i)} for i, (t, lv, arm) in enumerate(spec)]


def test_errors_are_charged_to_arms_and_an_insertion_to_the_glyph_before_it():
    row = _rendered([("a", 0, "matched"), ("b", 2, "unmatched")])
    s = h4.score_line(row, [{"token": "a", "confidence": 0.9}, {"token": "x", "confidence": 0.4},
                            {"token": "b", "confidence": 0.8}])  # fmt: skip
    assert [(m["correct"], m["inserted"], m["arm"]) for m in s["scored"]] == [
        (True, False, "matched"), (False, True, "matched"), (True, False, "unmatched")]  # fmt: skip
    assert s["errors"] == {"matched": 1} and s["counts"] == {"matched": 1, "unmatched": 1}


def test_an_insertion_at_the_start_of_a_line_goes_to_the_glyph_after_it():
    s = h4.score_line(_rendered([("a", 1, "unmatched")]), [{"token": "x", "confidence": 0.3},
                                                          {"token": "a", "confidence": 0.9}])  # fmt: skip
    assert s["scored"][0]["arm"] == "unmatched" and s["errors"] == {"unmatched": 1}


def test_a_deletion_keeps_its_level_and_arm():
    s = h4.score_line(_rendered([("a", 0, "matched"), ("b", 2, "matched")]), [{"token": "b", "confidence": 0.8}])
    assert [(g["level"], g["arm"]) for g in s["deleted"]] == [(0, "matched")]


def _scored(miss: float, lines: int = 300, per_line: int = 30, seed: int = 0, arm: str = "matched") -> list[dict]:
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(lines):
        conf = rng.uniform(0.5, 1.0, per_line)
        correct = rng.random(per_line) < conf - miss
        out.append({"scored": [{"confidence": c, "correct": bool(k), "inserted": False, "level": i % 3, "arm": arm,
                                "disputed": False, "source": "s"} for i, (c, k) in enumerate(zip(conf, correct))],
                    "deleted": [], "errors": {arm: 1}, "counts": {arm: per_line}})  # fmt: skip
    return out


def test_the_calibration_claim_needs_the_pooled_and_every_level_bound_under_0_05():
    good = h4.summarize({"R0": _scored(0.0), "R1": _scored(0.0), "R2": []})
    bad = h4.summarize({"R0": _scored(0.0), "R1": _scored(0.2), "R2": []})
    assert good["calibrated_on_synthetic_ink"] and not bad["calibrated_on_synthetic_ink"]
    assert set(good["matched"]["R1"]["levels"]) == {"0", "1", "2"}


def test_a_level_under_the_minimum_is_underpowered_and_blocks_the_claim():
    small = h4.summarize({"R0": _scored(0.0, lines=200, per_line=12), "R1": _scored(0.0, lines=200, per_line=12),
                          "R2": []})  # fmt: skip
    assert all(r["underpowered"] for r in small["matched"]["R1"]["levels"].values())
    assert not small["calibrated_on_synthetic_ink"]


def test_the_unmatched_arm_never_decides_the_claim():
    r1 = _scored(0.0) + _scored(0.3, arm="unmatched")
    out = h4.summarize({"R0": r1, "R1": r1, "R2": []})
    assert out["calibrated_on_synthetic_ink"]
    assert out["unmatched"]["R1"]["ece"]["hi"] > 0.05


def test_word_and_glyph_exemplars_never_come_from_test_or_dev_folios_and_words_not_from_validation():
    split = {"test": ["f50r"], "validation": ["f60r"]}
    words, glyphs = h4.exemplar_pages({"f1r", "f50r", "f60r", "f70r"}, split)
    assert words == ["f70r"] and glyphs == ["f60r", "f70r"]


def _instances(tmp_path, rows):
    (tmp_path / "f1r.json").write_text(json.dumps({"instances": rows}))
    return tmp_path


def _row(token, zl, column, gated=True, cls="agree", x=(0, 1)):
    cut = [[x[0], 0], [x[1], 0], [x[1], 5], [x[0], 5]]
    return {"locus": "f1r.1", "column": column, "token": token, "zl": zl, "gated": gated, "class": cls, "cut": cut}


def _word_rows(tokens, columns, zl=None):
    return [_row(t, (zl or tokens)[i], c, x=(10 * c, 10 * c + 9)) for i, (t, c) in enumerate(zip(tokens, columns))]


def test_the_exemplar_pool_keeps_instances_read_as_zl_reads_them(tmp_path):
    d = _instances(tmp_path, [_row("a", "a", 0), _row("b", "a", 1), _row("a", "a a", 2)])
    assert {t: [e.column for e in v] for t, v in h4.exemplar_pool(d, ["f1r"]).items()} == {"a": [0]}


def test_the_disputed_pool_takes_gated_disagree_columns_with_one_zl_codec_token(tmp_path):
    rows = [_row("x", "a", 0, cls="disagree"), _row("x", "a a", 1, cls="disagree"),
            _row("x", "b", 2, cls="disagree", gated=False), _row("x", "q", 3, cls="disagree"),
            _row("x", "a", 4)]  # fmt: skip
    pool = h4.disputed_pool(_instances(tmp_path, rows), ["f1r"], {"a", "b"})
    assert {t: [e.column for e in v] for t, v in pool.items()} == {"a": [0]}


@pytest.mark.parametrize("level", [0, 1, 2])
def test_degrade_returns_uint8_of_the_same_shape(level):
    out = h4.degrade(BOX, level, 0.5)
    assert out.dtype == np.uint8 and out.shape == BOX.shape
