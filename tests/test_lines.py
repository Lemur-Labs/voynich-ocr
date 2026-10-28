from voynich_ocr import lines as ln
from voynich_ocr.sta import Glyph

AAA = {"A1": "o0", "Ak": "o0", "B1": "d0", "E1": "i0~i0:b0", "Z1": "z0"}


def test_codec_gives_each_token_one_private_use_character_in_sorted_order():
    assert ln.codec(["o0", "d0", "o0", "i0~i0:b0"]) == {"d0": "", "i0~i0:b0": "", "o0": ""}


def test_label_maps_tokens_and_word_spaces():
    glyphs = [Glyph("A1", False, "."), Glyph("Ak", False, ""), Glyph("B1", True, ","), Glyph("E1", False, "-")]
    assert ln.tokens(glyphs, AAA) == ["o0", " ", "o0", "d0", " ", "i0~i0:b0"]


def test_line_with_an_unknown_glyph_has_no_label():
    assert ln.tokens([Glyph("A1", False, ""), Glyph("Z1", False, "")], AAA) is None


def test_early_stopping_pages_are_a_seeded_share_of_training_pages():
    pages = [f"f{i}r" for i in range(1, 41)]
    held = ln.early_stopping_pages(pages)
    assert len(held) == 4 and set(held) <= set(pages)
    assert held == ln.early_stopping_pages(list(reversed(pages)))


def test_file_stems_have_no_dots_so_kraken_finds_the_label_file():
    assert ln.stem("f103r.12") == "f103r_12"
