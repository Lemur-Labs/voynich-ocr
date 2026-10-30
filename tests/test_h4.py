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


def test_a_glyph_with_no_pool_still_takes_its_draws_so_later_glyphs_keep_theirs():
    pools = {"a": [_ex(i) for i in range(50)]}
    with_gap = h4.plan([[["z", "a"]]], pools, {}, [3])
    without = h4.plan([[["a", "a"]]], pools, {}, [3])
    assert with_gap["gaps"] == 1
    assert with_gap["R0"][0]["words"][0][-1]["exemplar"] == without["R0"][0]["words"][0][-1]["exemplar"]
    assert with_gap["R1"][0]["words"][0][-1]["level"] == without["R1"][0]["words"][0][-1]["level"]


def test_r0_and_r1_share_exemplars_and_r2_uses_a_disputed_one_where_it_exists():
    pools = {"a": [_ex(i) for i in range(50)], "b": [_ex(100 + i) for i in range(50)]}
    disputed = {"a": [_ex(900)]}
    p = h4.plan([[["a", "b"], ["a"]]], pools, disputed, [7])
    r0, r1, r2 = (p[k][0]["words"] for k in ("R0", "R1", "R2"))
    assert [g["exemplar"] for w in r0 for g in w] == [g["exemplar"] for w in r1 for g in w]
    assert all(g["level"] == 0 for w in r0 + r2 for g in w)
    assert [g["disputed"] for w in r2 for g in w] == [True, False, True]
    assert r2[0][0]["exemplar"] == _ex(900)
    assert p["R2"][0]["spaces"] == [7]


def test_alignment_prefers_the_diagonal_then_deletion():
    assert h4.alignment(["a", "b"], ["a", "b"]) == [(0, 0), (1, 1)]
    assert h4.alignment(["a"], ["a", "b"]) == [(0, 0), (None, 1)]
    assert h4.alignment(["a", "x", "b"], ["a", "b"]) == [(0, 0), (1, None), (2, 1)]


def test_score_line_marks_insertions_wrong_and_keeps_deleted_glyphs_with_their_level():
    row = [{"token": t, "level": lv, "exemplar": _ex(i)} for i, (t, lv) in enumerate([("a", 0), ("b", 2)])]
    s = h4.score_line(row, [{"token": "a", "confidence": 0.9}, {"token": "x", "confidence": 0.4}])
    assert [(m["correct"], m["inserted"]) for m in s["scored"]] == [(True, False), (False, False)]
    assert s["scored"][1]["level"] == 2 and s["deleted"] == []
    s = h4.score_line(row, [{"token": "b", "confidence": 0.8}])
    assert [g["level"] for g in s["deleted"]] == [0]


def _scored(miss: float, lines: int = 300, seed: int = 0) -> list[dict]:
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(lines):
        conf = rng.uniform(0.5, 1.0, 30)
        correct = rng.random(30) < conf - miss
        out.append({"scored": [{"confidence": c, "correct": bool(k), "inserted": False, "level": i % 3,
                                "disputed": False, "source": "s"} for i, (c, k) in enumerate(zip(conf, correct))],
                    "deleted": [], "distance": 1, "length": 30})  # fmt: skip
    return out


def test_the_calibration_claim_needs_the_pooled_and_every_level_bound_under_0_05():
    good = h4.summarize({"R0": _scored(0.0), "R1": _scored(0.0), "R2": []})
    bad = h4.summarize({"R0": _scored(0.0), "R1": _scored(0.2), "R2": []})
    assert good["calibrated_on_synthetic_ink"] and not bad["calibrated_on_synthetic_ink"]
    assert set(good["R1"]["levels"]) == {"0", "1", "2"}


def _instances(tmp_path, rows):
    (tmp_path / "f1r.json").write_text(json.dumps({"instances": rows}))
    return tmp_path


def _row(token, zl, column, gated=True, cls="agree", x=(0, 1)):
    cut = [[x[0], 0], [x[1], 0], [x[1], 5], [x[0], 5]]
    return {"locus": "f1r.1", "column": column, "token": token, "zl": zl, "gated": gated, "class": cls, "cut": cut}


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
