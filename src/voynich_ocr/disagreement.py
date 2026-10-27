import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from voynich_ocr import ivtff, sta
from voynich_ocr.align import align
from voynich_ocr.snapshot import RAW, ROOT

ORDER = ("ZL", "IT", "GC", "FG", "CD")
STA_FILES = {
    "ZL": "transliterations/sta/ZL3b.txt",
    "IT": "transliterations/sta/IT2a.txt",
    "GC": "transliterations/sta/GC2a_0.txt",
    "FG": "transliterations/sta/FG2a.txt",
    "CD": "transliterations/sta/CD2a_0.txt",
}
AAA_FILE = "bitrans/STA-aaa.bit"
SPLITS = ROOT / "docs" / "prereg" / "splits.json"
COARSE = frozenset({"CD", "FG"})
UNKNOWN = "?"
MAPS = {
    "full": ORDER,
    **{f"leave-{s}-out": tuple(t for t in ORDER if t != s) for s in ORDER},
    "leave-ZL-IT-out": ("GC", "FG", "CD"),
    "ZL-IT-GC": ("ZL", "IT", "GC"),
}
# Section rates use the fixed set {ZL, IT, GC, FG}: the leave-CD-out map, on loci all four cover.
SECTION_MAP = "leave-CD-out"
SECTION_VARIABLES = {"I": "illustration", "L": "currier_language", "H": "hand"}
GATED_TIER = 3


@dataclass(frozen=True)
class Source:
    loci: dict[str, list[sta.Glyph]]
    codes: frozenset[str]


@dataclass(frozen=True)
class Locus:
    id: str
    page: str
    variables: dict[str, str]


@dataclass(frozen=True)
class Column:
    locus: str
    page: str
    index: int
    tier: int
    readings: dict[str, tuple[str, ...]]
    codes: dict[str, tuple[str, ...]]
    contributing: tuple[str, ...]
    cls: str
    zl_uncertain: bool

    @property
    def gated(self) -> bool:
        return (
            self.tier >= GATED_TIER
            and len(self.contributing) >= GATED_TIER
            and self.cls in ("agree", "disagree")
            and not self.zl_uncertain
        )


@dataclass(frozen=True)
class Boundary:
    locus: str
    page: str
    cls: str
    spaces: dict[str, str]


@dataclass(frozen=True)
class Inputs:
    sources: dict[str, Source]
    loci: list[Locus]
    aaa: dict[str, str]


def load_source(text: str) -> tuple[Source, dict[str, ivtff.Locus]]:
    t = ivtff.parse(text)
    loci = {lo.id: lo for lo in t.loci if lo.exists}
    glyphs = {k: sta.glyphs(lo.text) for k, lo in loci.items()}
    return Source(glyphs, frozenset(g.code for gs in glyphs.values() for g in gs)), loci


def load(raw: Path = RAW) -> Inputs:
    sources, parsed = {}, {}
    for name in ORDER:
        sources[name], parsed[name] = load_source((raw / STA_FILES[name]).read_text())
    page_order = {p: i for i, p in enumerate(ivtff.parse((raw / STA_FILES["ZL"]).read_text()).pages)}
    ids = {k for name in ORDER for k in parsed[name]}
    loci = []
    for k in ids:
        first = next(parsed[name][k] for name in ORDER if k in parsed[name])
        loci.append(Locus(k, first.page, first.variables))
    loci.sort(key=lambda lo: (page_order[lo.page], int(lo.id.split(".")[1])))
    return Inputs(sources, loci, sta.load_aaa((raw / AAA_FILE).read_text()))


def token(code: str, aaa: dict[str, str]) -> str:
    return UNKNOWN if code == sta.UNKNOWN else aaa[code]


def _zl_uncertain(columns: list[list[int | None]], zl: int, glyphs: list[sta.Glyph]) -> list[bool]:
    """A ZL alternative's first option is uncertain, and so is any ZL gap next to it."""
    alt = [c[zl] is not None and glyphs[c[zl]].alternative for c in columns]
    out = list(alt)
    for i, c in enumerate(columns):
        if c[zl] is not None:
            continue
        left = next((alt[j] for j in range(i - 1, -1, -1) if columns[j][zl] is not None), False)
        right = next((alt[j] for j in range(i + 1, len(columns)) if columns[j][zl] is not None), False)
        out[i] = left or right
    return out


def _runs(tokens: list[list[str | None]]) -> list[tuple[int, int]]:
    """Spans of consecutive columns whose readings, gaps aside, are all one token."""
    spans = []
    i = 0
    while i < len(tokens):
        kinds = set(tokens[i]) - {None}
        j = i + 1
        if len(kinds) == 1 and UNKNOWN not in kinds:
            while j < len(tokens) and set(tokens[j]) - {None} == kinds:
                j += 1
        spans.append((i, j))
        i = j
    return spans


def classify(
    readings: dict[str, tuple[str, ...]], codes: dict[str, tuple[str, ...]], expressible: dict[str, frozenset[str]]
) -> tuple[tuple[str, ...], str]:
    """Contributing sources and the column's class. A source is dropped where a competing reading, one that
    differs from its own, uses an STA code its file never produces."""
    contributing = tuple(
        s
        for s in readings
        if all(set(codes[t]) <= expressible[s] for t in readings if readings[t] != readings[s])
    )
    if any(UNKNOWN in r for r in readings.values()):
        return contributing, "unknown"
    if len(contributing) < 2:
        return contributing, "unscorable"
    values = {readings[s] for s in contributing}
    if len(values) <= 1:
        return contributing, "agree"
    gap_side = {s for s in contributing if not readings[s]}
    token_side = set(contributing) - gap_side
    if gap_side and len(values) == 2 and (gap_side <= COARSE or token_side <= COARSE):
        return contributing, "granularity"
    return contributing, "disagree"


def locus_columns(locus: Locus, inputs: Inputs, names: tuple[str, ...]) -> tuple[list[Column], list[Boundary]]:
    covering = [s for s in names if locus.id in inputs.sources[s].loci]
    glyphs = {s: inputs.sources[s].loci[locus.id] for s in covering}
    tokens = {s: [token(g.code, inputs.aaa) for g in glyphs[s]] for s in covering}
    aligned = align([tokens[s] for s in covering], UNKNOWN)
    at = [[tokens[s][c[k]] if c[k] is not None else None for k, s in enumerate(covering)] for c in aligned]
    uncertain = (
        _zl_uncertain(aligned, covering.index("ZL"), glyphs["ZL"]) if "ZL" in covering else [False] * len(aligned)
    )
    expressible = {s: inputs.sources[s].codes for s in covering}

    columns = []
    for start, end in _runs(at):
        readings, codes = {}, {}
        for k, s in enumerate(covering):
            idx = [c[k] for c in aligned[start:end] if c[k] is not None]
            readings[s] = tuple(tokens[s][i] for i in idx)
            codes[s] = tuple(glyphs[s][i].code for i in idx)
        contributing, cls = classify(readings, codes, expressible)
        columns.append(
            Column(
                locus.id,
                locus.page,
                len(columns),
                len(covering),
                readings,
                codes,
                contributing,
                cls,
                any(uncertain[start:end]),
            )
        )

    boundaries = []
    for c in aligned:
        spaces = {}
        for k, s in enumerate(covering):
            i = c[k]
            if i is None or i == len(glyphs[s]) - 1 or tokens[s][i] == UNKNOWN:
                continue
            spaces[s] = {"-": "."}.get(glyphs[s][i].space_after, glyphs[s][i].space_after)
        if len(spaces) < 2:
            continue
        values = set(spaces.values())
        cls = "uncertain" if "," in values else ("agree" if len(values) == 1 else "disagree")
        boundaries.append(Boundary(locus.id, locus.page, cls, spaces))
    return columns, boundaries


def build(inputs: Inputs, names: tuple[str, ...]) -> tuple[list[Column], list[Boundary]]:
    columns, boundaries = [], []
    for locus in inputs.loci:
        c, b = locus_columns(locus, inputs, names)
        columns += c
        boundaries += b
    return columns, boundaries


def column_row(c: Column) -> str:
    readings = ";".join(f"{s}={' '.join(c.readings[s]) or '-'}" for s in c.readings)
    codes = ";".join(f"{s}={''.join(c.codes[s]) or '-'}" for s in c.codes)
    flag = "zl_uncertain" if c.zl_uncertain else ""
    return "\t".join([c.locus, str(c.index), str(c.tier), c.cls, flag, ",".join(c.contributing), readings, codes])


COLUMN_HEADER = "locus\tcolumn\ttier\tclass\tflag\tcontributing\treadings\tcodes"


def _rate(columns: list[Column]) -> dict:
    gated = [c for c in columns if c.gated]
    n_dis = sum(c.cls == "disagree" for c in gated)
    return {
        "columns": len(columns),
        "classes": dict(sorted(Counter(c.cls for c in columns).items())),
        "zl_uncertain": sum(c.zl_uncertain for c in columns),
        "gated": len(gated),
        "gated_disagree": n_dis,
        "gated_rate": round(n_dis / len(gated), 6) if gated else None,
        "gated_by_contributors": {
            str(k): [sum(c.cls == "disagree" for c in g), len(g)]
            for k in sorted({len(c.contributing) for c in gated})
            for g in [[c for c in gated if len(c.contributing) == k]]
        },
    }


def pairwise(columns: list[Column], names: tuple[str, ...], top: int = 15) -> dict:
    """Per pair, over gated columns both contribute to: how often their readings differ, and the commonest
    differing pairs."""
    out = {}
    for a, b in combinations(names, 2):
        n, confusions = 0, Counter()
        for c in columns:
            if not c.gated or a not in c.contributing or b not in c.contributing:
                continue
            n += 1
            if c.readings[a] != c.readings[b]:
                confusions[(" ".join(c.readings[a]) or "-", " ".join(c.readings[b]) or "-")] += 1
        differ = sum(confusions.values())
        out[f"{a}-{b}"] = {
            "columns": n,
            "differ": differ,
            "rate": round(differ / n, 6) if n else None,
            "top": [[x, y, k] for (x, y), k in sorted(confusions.items(), key=lambda kv: (-kv[1], kv[0]))[:top]],
        }
    return out


def unplaced_unknowns(columns: list[Column], inputs: Inputs, names: tuple[str, ...], test: set[str]) -> dict:
    """`?` that a wildcard run left out because it covered fewer columns than it had."""
    shown = {lo.id for lo in inputs.loci if lo.page not in test}
    out = {}
    for s in names:
        written = sum(
            g.code == sta.UNKNOWN for k, gs in inputs.sources[s].loci.items() if k in shown for g in gs
        )
        placed = sum(c.readings[s].count(UNKNOWN) for c in columns if c.locus in shown and s in c.readings)
        out[s] = {"written": written, "unplaced": written - placed}
    return out


def summarize(maps: dict[str, tuple[list[Column], list[Boundary]]], inputs: Inputs, test: set[str]) -> dict:
    """Published figures. Test pages are withheld (VO-019), so nothing here is computed on them."""
    loci = inputs.loci
    pages_meta = {}
    for lo in loci:
        pages_meta.setdefault(lo.page, lo.variables)
    hand = {lo.id: lo.variables.get("H", "?") for lo in loci}
    summary = {"withheld_test_pages": len(test), "maps": {}}
    for name, (columns, boundaries) in maps.items():
        shown = [c for c in columns if c.page not in test]
        b_shown = [b for b in boundaries if b.page not in test]
        summary["maps"][name] = {
            "sources": list(MAPS[name]),
            "overall": _rate(shown),
            "by_tier": {str(t): _rate([c for c in shown if c.tier == t]) for t in sorted({c.tier for c in shown})},
            "word_breaks": dict(sorted(Counter(b.cls for b in b_shown).items())),
        }
    columns = [c for c in maps["full"][0] if c.page not in test]
    summary["pairwise"] = pairwise(columns, ORDER)
    summary["unplaced_unknowns"] = unplaced_unknowns(maps["full"][0], inputs, ORDER, test)
    by_page: dict[str, list[Column]] = {}
    for c in columns:
        by_page.setdefault(c.page, []).append(c)
    breaks_by_page = Counter(b.page for b in maps["full"][1] if b.page not in test and b.cls == "disagree")
    summary["pages"] = {
        p: {**_rate(cs), "word_break_disagree": breaks_by_page[p]} for p, cs in by_page.items()
    }
    section_columns = [c for c in maps[SECTION_MAP][0] if c.page not in test and c.tier == len(MAPS[SECTION_MAP])]
    summary["sections"] = {}
    for var, label in SECTION_VARIABLES.items():
        groups: dict[str, list[Column]] = {}
        for c in section_columns:
            value = hand[c.locus] if var == "H" else pages_meta[c.page].get(var, "?")
            groups.setdefault(value, []).append(c)
        summary["sections"][label] = {k: _rate(v) for k, v in sorted(groups.items())}
    return summary


def test_pages(path: Path = SPLITS) -> set[str]:
    return set(json.loads(path.read_text())["test"])


def write(out: Path, inputs: Inputs, maps: dict[str, tuple[list[Column], list[Boundary]]], test: set[str]) -> None:
    (out / "columns").mkdir(parents=True, exist_ok=True)
    (out / "published").mkdir(parents=True, exist_ok=True)
    for name, (columns, _) in maps.items():
        rows = [COLUMN_HEADER] + [column_row(c) for c in columns]
        (out / "columns" / f"{name}.tsv").write_text("\n".join(rows) + "\n")
        shown = [COLUMN_HEADER] + [column_row(c) for c in columns if c.page not in test]
        (out / "published" / f"{name}.tsv").write_text("\n".join(shown) + "\n")
    summary = summarize(maps, inputs, test)
    (out / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="disagreement")
    p.add_argument("--out", type=Path, default=ROOT / "build" / "map")
    args = p.parse_args(argv)
    inputs = load()
    maps = {name: build(inputs, names) for name, names in MAPS.items()}
    write(args.out, inputs, maps, test_pages())
    return 0


if __name__ == "__main__":
    sys.exit(main())
