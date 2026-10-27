from voynich_ocr import splits

HEADER = "#=IVTFF Eva- 2.0 M 5\n"


def _file(pages):
    return HEADER + "".join(f"<{p}>      <! $I={i} $L={lang}>\n<{p}.1,@P0>  daiin\n" for p, i, lang in pages)


PAGES = [(f"f{n}r", "H" if n % 3 else "S", "A" if n % 2 else "B") for n in range(1, 61)]


def _native(drop_from_fg=()):
    full = _file(PAGES)
    fg = _file([p for p in PAGES if p[0] not in drop_from_fg])
    return {"ZL": full, "IT": full, "GC": full, "FG": fg, "CD": _file(PAGES[:10])}


def test_page_headers_read_illustration_and_language_variables():
    assert splits.page_headers(_file([("f89v2", "Z", "B")])) == {"f89v2": {"I": "Z", "L": "B"}}


def test_splits_are_deterministic_and_disjoint():
    a, b = splits.make_splits(_native()), splits.make_splits(_native())
    assert a == b
    assert not set(a["test"]) & set(a["validation"])


def test_test_pages_need_four_sources_but_not_currier():
    s = splits.make_splits(_native(drop_from_fg={"f1r", "f2r", "f3r"}))
    assert s["eligible_pages"] == 57
    assert not {"f1r", "f2r", "f3r"} & set(s["test"])
    assert set(s["test"]) - {p for p, _, _ in PAGES[:10]}
