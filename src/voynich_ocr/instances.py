import argparse
import json
import sys
from pathlib import Path

import numpy as np

from voynich_ocr import disagreement as d
from voynich_ocr import freeze, lines, recognize, segment
from voynich_ocr.snapshot import ROOT

OUT = ROOT / "build" / "instances"


def zl_tokens(inputs: d.Inputs, locus: str) -> list[str]:
    return [d.token(g.code, inputs.aaa) for g in inputs.sources["ZL"].loci.get(locus, [])]


def pair_rows(
    sizes: list[tuple[int, int]],
    ids: list[str],
    labels: dict[str, list[str] | None],
    zl: dict[str, list[str]],
    decoded: list[list[str]],
) -> tuple[dict[str, int], str]:
    """Loci to row indices. When the counts match, rows pair by count if the labelled lines pass training's
    `lines.screen`; unlabelled (`?`) lines stay unless taller than the labelled ones allow. Otherwise rows pair by
    text over the single rows."""
    labelled = [i for i, k in enumerate(ids) if labels[k] is not None] if len(sizes) == len(ids) else []
    if labelled:
        keep, ok = lines.screen([sizes[i] for i in labelled], [len(labels[ids[i]]) for i in labelled])
        if ok:
            tallest = lines.TALL * float(np.median([sizes[i][1] for i in labelled]))
            kept = {i for i, k in zip(labelled, keep, strict=True) if k}
            kept |= {i for i, k in enumerate(ids) if labels[k] is None and sizes[i][1] <= tallest}
            return {ids[i]: i for i in sorted(kept)}, "count"
    kept = [i for i, k in enumerate(lines.single_row([h for _, h in sizes])) if k]
    by_text = recognize.assign_by_text([decoded[i] for i in kept], zl)
    return {k: kept[j] for k, j in by_text.items()}, "text"


def pair_rows_blind(sizes: list[tuple[int, int]], ids: list[str]) -> tuple[dict[str, int], str]:
    """Loci to row indices in order when the page's single rows match its loci in number; no transliteration read."""
    kept = [i for i, k in enumerate(lines.single_row([h for _, h in sizes])) if k]
    if len(kept) != len(ids):
        return {}, "blind"
    return dict(zip(ids, kept, strict=True)), "blind"


def columns_for(
    locus: d.Locus, recognized: list[str], inputs: d.Inputs, names: tuple[str, ...]
) -> tuple[list[d.Column], list[int | None], int]:
    """The locus's columns in the map over `names`, each recognized glyph's column there, and the insertions."""
    cols, _ = d.locus_columns(locus, inputs, names)
    where, n = recognize.align_to_columns(recognized, recognize.consensus([c.readings for c in cols]))
    return cols, where, n


def page_instances(
    model, page: str, inputs: d.Inputs, loci: list[d.Locus], tokens: dict[str, str], blind: bool = False
) -> dict:
    """Recognized glyphs of one page's paragraph rows, each tied to its map column through `pair_rows`, or
    `pair_rows_blind` when `blind`."""
    rows = segment.page_lines(json.loads((segment.OUT / f"{page}.json").read_text()), segment.height(page))
    read = recognize.read_page(model, page, rows)
    decoded = [[tokens[g["char"]] for g in row if g["char"] != lines.SPACE] for row in read]
    sizes = [im.size for _, im in lines.line_images(page, {str(i): r for i, r in enumerate(rows)})]
    ids = [lo.id for lo in loci]
    if blind:
        pairs, rule = pair_rows_blind(sizes, ids)
    else:
        zl = inputs.sources["ZL"].loci
        labels = {k: lines.tokens(zl.get(k, []), inputs.aaa) for k in ids}
        pairs, rule = pair_rows(sizes, ids, labels, {k: zl_tokens(inputs, k) for k in ids}, decoded)
    out = []
    inserted = 0
    for locus in loci:
        if locus.id not in pairs:
            continue
        glyphs = [g for g in read[pairs[locus.id]] if g["char"] != lines.SPACE]
        cols, where, n = columns_for(locus, [tokens[g["char"]] for g in glyphs], inputs, d.MAPS["full"])
        inserted += n
        for g, k in zip(glyphs, where, strict=True):
            if k is None:
                continue
            c = cols[k]
            out.append({
                "page": page, "locus": locus.id, "column": k, "token": tokens[g["char"]],
                "confidence": g["confidence"], "cut": g["cut"], "class": c.cls, "tier": c.tier,
                "gated": c.gated, "zl": " ".join(c.readings.get("ZL", ())),
                "readings": {s: " ".join(c.readings[s]) for s in c.contributing},
            })  # fmt: skip
    return {"rule": rule, "loci": len(ids), "pairs": pairs, "inserted": inserted, "instances": out}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="instances")
    p.add_argument("model", type=Path)
    p.add_argument("pages", nargs="*", help="default: every segmented non-test page")
    p.add_argument("--test", action="store_true", help="also test pages (only once configs are frozen)")
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--blind", action="store_true", help="pair rows to loci without reading any transliteration")
    args = p.parse_args(argv)
    if args.blind and args.out == OUT:
        raise SystemExit("blind pairing needs its own --out")
    if args.test:
        freeze.require(args.model)
    test = d.test_pages()
    if not args.test and (blocked := sorted(set(args.pages) & test)):
        raise SystemExit(f"test pages need --test: {blocked}")
    pages = [p for p in args.pages or sorted(f.stem for f in segment.OUT.glob("*.json")) if args.test or p not in test]
    inputs = d.load()
    paragraph = lines.paragraph_loci()
    by_id = {lo.id: lo for lo in inputs.loci}
    codec = json.loads((lines.OUT / "codec.json").read_text())
    tokens = {ch: t for t, ch in codec.items()}
    model = recognize.load(args.model)
    args.out.mkdir(parents=True, exist_ok=True)
    for page in pages:
        loci = [by_id[k] for k in paragraph.get(page, []) if k in by_id]
        if not loci:
            continue
        result = page_instances(model, page, inputs, loci, tokens, args.blind)
        (args.out / f"{page}.json").write_text(json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
