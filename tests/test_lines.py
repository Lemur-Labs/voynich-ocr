import numpy as np
from PIL import Image

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


def test_line_images_much_taller_than_their_page_median_are_dropped():
    assert ln.single_row([100, 110, 105, 170, 95]) == [True, True, True, False, True]


def test_page_whose_line_widths_do_not_track_label_lengths_is_unpaired():
    widths = [10.0, 12.0, 14.0, 16.0, 18.0, 20.0]
    assert ln.paired(widths, [20, 24, 28, 32, 36, 40])
    assert not ln.paired(widths, [40, 36, 32, 28, 24, 20])
    assert ln.paired(widths[:5], [40, 36, 32, 28, 24])


def test_paper_fill_replaces_only_the_black_polygon_fill():
    a = np.full((10, 20, 3), 200, dtype=np.uint8)
    a[:3] = 0
    a[5, 5] = (60, 40, 20)
    out = np.asarray(ln.paper_fill(Image.fromarray(a)))
    assert (out[:3] == 200).all()
    assert tuple(out[5, 5]) == (60, 40, 20)


def test_paper_fill_leaves_an_all_black_image_alone():
    black = Image.new("RGB", (8, 4))
    assert np.asarray(ln.paper_fill(black)).max() == 0
