import re
from dataclasses import dataclass

_HEADER = re.compile(r"^#=IVTFF (.{4}) (\d+\.\d+) ([MDA])(?: .*)?$")
_PAGE = re.compile(r"^<(f[0-9a-z]+|fRos)>(?:\s+<!(.*)>)?\s*$")
_LOCUS = re.compile(r"^<(f[0-9a-z]+|fRos)\.(\d{1,3}),([@+*=&~/!])([A-Z][0-9a-z])(?:;(.))?>(.*)$")
_VAR = re.compile(r"\$([A-Z])=(\S)")
_TAG = re.compile(r"<@([A-Z])=(.)>")
COMMENT = re.compile(r"<![^>]*>")
DEDICATED = re.compile(r"<[%$]>|<@[A-Z]=.>")
DRAWING = re.compile(r"<[-~]>")
_ALTERNATIVE = re.compile(r"\[([^\]]*)\]")


@dataclass(frozen=True)
class Locus:
    page: str
    num: int
    locator: str
    type: str
    transcriber: str | None
    text: str
    variables: dict[str, str]

    @property
    def id(self) -> str:
        return f"{self.page}.{self.num}"

    @property
    def exists(self) -> bool:
        """The `!` locator marks a transliteration item for text that is not in the manuscript."""
        return self.locator != "!"


@dataclass(frozen=True)
class Transliteration:
    alphabet: str
    pages: dict[str, dict[str, str]]
    loci: list[Locus]


def _joined_lines(lines: list[str]) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    pending = False
    for n, line in enumerate(lines, start=1):
        if line.startswith("/"):
            if not pending:
                raise ValueError(f"line {n}: continuation without a preceding '/'")
            out[-1] = (out[-1][0], out[-1][1] + line[1:])
        else:
            if pending:
                raise ValueError(f"line {n}: line {out[-1][0]} ends in '/' but this line does not continue it")
            out.append((n, line))
        pending = out[-1][1].endswith("/") if out else False
        if pending:
            out[-1] = (out[-1][0], out[-1][1][:-1])
    if pending:
        raise ValueError("file ends inside a continued line")
    return out


def parse(text: str) -> Transliteration:
    lines = text.splitlines()
    header = _HEADER.match(lines[0]) if lines else None
    if not header:
        raise ValueError("line 1: not an IVTFF header")
    pages: dict[str, dict[str, str]] = {}
    loci: list[Locus] = []
    page = None
    tags: dict[str, str] = {}
    for n, line in _joined_lines(lines[1:]):
        n += 1
        if line.startswith("#") or not line.strip():
            continue
        if m := _PAGE.match(line):
            page = m.group(1)
            if page in pages:
                raise ValueError(f"line {n}: page {page} repeated")
            pages[page] = dict(_VAR.findall(m.group(2) or ""))
            tags = {}
            continue
        m = _LOCUS.match(line)
        if not m:
            raise ValueError(f"line {n}: neither a comment, a page header nor a locus: {line[:40]!r}")
        if m.group(1) != page:
            raise ValueError(f"line {n}: locus on page {m.group(1)} under header {page}")
        body = m.group(6).strip()
        tags.update(_TAG.findall(COMMENT.sub("", body)))
        loci.append(
            Locus(
                page=page,
                num=int(m.group(2)),
                locator=m.group(3),
                type=m.group(4),
                transcriber=m.group(5),
                text=body,
                variables={**pages[page], **tags},
            )
        )
    return Transliteration(alphabet=header.group(1), pages=pages, loci=loci)


def plain_text(text: str) -> str:
    """The locus text as `ivtt -x2` writes it: comments and paragraph marks removed, the first alternative
    reading taken, drawing intrusions written as a word space, ligature braces and `@nnn;` kept."""
    text = COMMENT.sub("", text)
    text = DEDICATED.sub("", text)
    text = DRAWING.sub(".", text)
    text = _ALTERNATIVE.sub(lambda m: m.group(1).split(":")[0], text)
    return re.sub(r"\s+", "", text)
