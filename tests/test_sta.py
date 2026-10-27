from voynich_ocr.sta import Glyph, glyphs


def test_first_alternative_is_taken_and_flagged():
    assert glyphs("A1[B1:B2]A2") == [Glyph("A1", False, ""), Glyph("B1", True, ""), Glyph("A2", False, "")]


def test_empty_first_alternative_flags_its_neighbour():
    assert glyphs("A1.[:A2]B1") == [Glyph("A1", True, "."), Glyph("B1", False, "")]
    assert glyphs("[:A2]B1") == [Glyph("B1", True, "")]


def test_spaces_and_markup():
    assert glyphs("<%>A1.B1,<!x>C1<->D1<$>") == [
        Glyph("A1", False, "."),
        Glyph("B1", False, ","),
        Glyph("C1", False, "-"),
        Glyph("D1", False, ""),
    ]
