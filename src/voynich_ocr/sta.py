import re
from dataclasses import dataclass

from voynich_ocr.ivtff import COMMENT, DEDICATED, DRAWING

# Every native `?` becomes this code (STA-Eva_def.bit, STA-v101_def.bit).
UNKNOWN = "Z1"
_CODE = re.compile(r"[A-Z][0-9a-z]")


@dataclass(frozen=True)
class Glyph:
    code: str
    alternative: bool
    space_after: str


def load_aaa(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or not lines[0].startswith("##BIT1 STA1 aaa"):
        raise ValueError("not an STA to aaa rules file")
    table = {}
    for line in lines[1:]:
        if line.startswith(("#", "<")) or not line.strip():
            continue
        code, value = line.split()
        if code in table:
            raise ValueError(f"duplicate rule for {code}")
        table[code] = value
    return table


def _scan(text: str, alternative: bool, out: list[Glyph]) -> None:
    i = 0
    # An alternative whose first option is empty (`[:A2]`) emits nothing; its neighbour carries the flag.
    pending = False
    while i < len(text):
        c = text[i]
        if c in ".,-":
            # CD2a puts a drawing intrusion before the first glyph of some loci; it separates nothing.
            if out:
                out[-1] = Glyph(out[-1].code, out[-1].alternative, c)
            i += 1
        elif c == "[":
            end = text.index("]", i)
            before = len(out)
            _scan(text[i + 1 : end].split(":")[0], True, out)
            if len(out) == before:
                if out:
                    out[-1] = Glyph(out[-1].code, True, out[-1].space_after)
                else:
                    pending = True
            i = end + 1
        elif _CODE.fullmatch(text, i, i + 2):
            out.append(Glyph(text[i : i + 2], alternative or pending, ""))
            pending = False
            i += 2
        else:
            raise ValueError(f"unexpected {c!r} at {i} in {text!r}")


def glyphs(text: str) -> list[Glyph]:
    """STA codes of one locus, the first alternative taken. `space_after` is "." (word space), "," (uncertain
    space), "-" (drawing intrusion) or ""."""
    text = DEDICATED.sub("", COMMENT.sub("", text))
    text = DRAWING.sub("-", text)
    out: list[Glyph] = []
    _scan(re.sub(r"\s+", "", text), False, out)
    return out
