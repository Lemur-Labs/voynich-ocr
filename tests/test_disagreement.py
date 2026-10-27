from voynich_ocr import disagreement as d
from voynich_ocr.sta import Glyph

AAA = {"A1": "o0", "A2": "y0", "Ak": "o0", "B1": "d0", "B2": "e0", "E1": "i0", "Q1": "k0", "Z1": "z0"}
ALL = frozenset(AAA)


def _inputs(texts: dict[str, list[Glyph]], codes: dict[str, frozenset[str]] | None = None) -> d.Inputs:
    sources = {
        s: d.Source({"f1r.1": g} if g is not None else {}, (codes or {}).get(s, ALL)) for s, g in texts.items()
    }
    return d.Inputs(sources, [d.Locus("f1r.1", "f1r", {})], AAA)


def _g(codes: str, alt: str = "", spaces: dict[int, str] | None = None) -> list[Glyph]:
    pairs = [codes[i : i + 2] for i in range(0, len(codes), 2)]
    return [Glyph(c, str(i) in alt, (spaces or {}).get(i, "")) for i, c in enumerate(pairs)]


def _columns(texts, codes=None):
    return d.locus_columns(d.Locus("f1r.1", "f1r", {}), _inputs(texts, codes), tuple(texts))


def test_identical_sources_agree_everywhere():
    cols, _ = _columns({s: _g("A1B1E1") for s in d.ORDER})
    assert [c.cls for c in cols] == ["agree"] * 3


def test_tokens_compare_after_aaa_so_codes_with_one_stroke_string_agree():
    cols, _ = _columns({"ZL": _g("A1B1"), "IT": _g("AkB1"), "GC": _g("A1B1")})
    assert [c.cls for c in cols] == ["agree", "agree"]


def test_gap_inside_an_identical_run_is_one_disagreement_wherever_it_falls():
    cols, _ = _columns({"ZL": _g("B1E1E1E1A2"), "IT": _g("B1E1E1A2"), "GC": _g("B1E1E1E1A2")})
    assert [(c.cls, c.readings["IT"]) for c in cols] == [
        ("agree", ("d0",)),
        ("disagree", ("i0", "i0")),
        ("agree", ("y0",)),
    ]


def test_tier_counts_covering_sources_before_the_mask():
    texts = {"ZL": _g("A1"), "IT": _g("A1"), "GC": _g("A1"), "FG": None, "CD": None}
    cols, _ = _columns(texts)
    assert cols[0].tier == 3


def test_unknown_in_any_source_is_its_own_class():
    cols, _ = _columns({"ZL": _g("A1B1"), "IT": _g("A1Z1"), "GC": _g("A1B1")})
    assert [c.cls for c in cols] == ["agree", "unknown"]


def test_source_that_never_writes_a_competing_code_is_masked():
    codes = {"ZL": ALL, "IT": frozenset({"A1", "B1"}), "GC": ALL}
    cols, _ = _columns({"ZL": _g("A1Q1"), "IT": _g("A1B1"), "GC": _g("A1Q1")}, codes)
    assert cols[1].contributing == ("ZL", "GC")
    assert cols[1].cls == "agree"
    assert cols[1].tier == 3


def test_source_is_masked_only_by_readings_that_differ_from_its_own():
    codes = {"ZL": frozenset({"A1", "B1"}), "IT": frozenset({"A1", "B1"}), "GC": ALL}
    cols, _ = _columns({"ZL": _g("A1B1"), "IT": _g("A1B1"), "GC": _g("AkB1")}, codes)
    assert cols[0].contributing == ("ZL", "IT", "GC")
    assert cols[0].cls == "agree"


def test_column_left_with_one_source_after_the_mask_is_unscorable_not_agreement():
    codes = {"ZL": frozenset({"A1", "B1"}), "IT": frozenset({"A1", "B1"}), "GC": ALL}
    cols, _ = _columns({"ZL": _g("A1B1"), "IT": _g("A1B1"), "GC": _g("A1Q1")}, codes)
    assert (cols[1].contributing, cols[1].cls, cols[1].gated) == (("GC",), "unscorable", False)


def test_gap_against_a_token_from_a_coarse_source_is_granularity():
    cols, _ = _columns({"ZL": _g("A1E1B1"), "IT": _g("A1E1B1"), "GC": _g("A1E1B1"), "FG": _g("A1B1")})
    assert [c.cls for c in cols] == ["agree", "granularity", "agree"]


def test_gap_against_a_token_between_fine_sources_is_disagreement():
    cols, _ = _columns({"ZL": _g("A1E1B1"), "IT": _g("A1B1"), "GC": _g("A1E1B1"), "FG": _g("A1E1B1")})
    assert [c.cls for c in cols] == ["agree", "disagree", "agree"]


def test_zl_alternative_and_its_neighbouring_gaps_are_flagged():
    cols, _ = _columns({"ZL": _g("A1E1B1", alt="1"), "IT": _g("A1E1Q1B1"), "GC": _g("A1E1Q1B1")})
    assert [(c.cls, c.zl_uncertain) for c in cols] == [
        ("agree", False),
        ("agree", True),
        ("disagree", True),
        ("agree", False),
    ]
    assert not any(c.gated for c in cols[1:3])


def test_word_breaks_compare_per_boundary_and_drawing_counts_as_a_space():
    texts = {
        "ZL": _g("A1B1E1", spaces={0: "."}),
        "IT": _g("A1B1E1", spaces={0: "-"}),
        "GC": _g("A1B1E1", spaces={1: "."}),
    }
    _, boundaries = _columns(texts)
    assert [b.cls for b in boundaries] == ["disagree", "disagree"]
    assert boundaries[0].spaces == {"ZL": ".", "IT": ".", "GC": ""}


def test_gated_columns_need_tier_three():
    cols, _ = _columns({"ZL": _g("A1"), "IT": _g("A1")})
    assert not cols[0].gated


def test_gated_columns_need_three_contributing_sources_after_the_mask():
    codes = {"ZL": ALL, "IT": frozenset({"A1", "B1"}), "GC": ALL}
    cols, _ = _columns({"ZL": _g("A1Q1"), "IT": _g("A1B1"), "GC": _g("A1Q1")}, codes)
    assert (cols[1].tier, cols[1].contributing, cols[1].cls) == (3, ("ZL", "GC"), "agree")
    assert not cols[1].gated
    assert cols[0].gated
