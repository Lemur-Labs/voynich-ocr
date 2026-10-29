import argparse
import json
import sys
from pathlib import Path

from voynich_ocr import disagreement as d
from voynich_ocr import freeze, lines, recognize, segment
from voynich_ocr.snapshot import ROOT

OUT = ROOT / "build" / "instances"


def zl_tokens(inputs: d.Inputs, locus: str) -> list[str]:
    return [d.token(g.code, inputs.aaa) for g in inputs.sources["ZL"].loci.get(locus, [])]


def pair_rows(
    sizes: list[tuple[float, float]], ids: list[str], zl: dict[str, list[str]], decoded: list[list[str]]
) -> tuple[dict[str, int], str]:
    """Loci to row indices. Rows pair by count, as in training, when the counts match before tall rows are dropped
    and the kept rows' widths track their loci's lengths (`lines.paired`); else by text over the kept rows."""
    kept = [i for i, k in enumerate(lines.single_row([h for _, h in sizes])) if k]
    widths = [sizes[i][0] / sizes[i][1] for i in kept]
    if len(sizes) == len(ids) and lines.paired(widths, [len(zl[ids[i]]) for i in kept]):
        return {ids[i]: i for i in kept}, "count"
    by_text = recognize.assign_by_text([decoded[i] for i in kept], zl)
    return {k: kept[j] for k, j in by_text.items()}, "text"


def page_instances(model, page: str, inputs: d.Inputs, loci: list[d.Locus], tokens: dict[str, str]) -> dict:
    """Recognized glyphs of one page's paragraph rows, each tied to its map column through `pair_rows`."""
    rows = segment.page_lines(json.loads((segment.OUT / f"{page}.json").read_text()), segment.height(page))
    read = recognize.read_page(model, page, rows)
    decoded = [[tokens[g["char"]] for g in row if g["char"] != lines.SPACE] for row in read]
    sizes = [
        (max(p[0] for p in r["boundary"]) - min(p[0] for p in r["boundary"]),
         max(p[1] for p in r["boundary"]) - min(p[1] for p in r["boundary"]))
        for r in rows
    ]  # fmt: skip
    ids = [lo.id for lo in loci]
    pairs, rule = pair_rows(sizes, ids, {k: zl_tokens(inputs, k) for k in ids}, decoded)
    out = []
    inserted = 0
    for locus in loci:
        if locus.id not in pairs:
            continue
        cols, _ = d.locus_columns(locus, inputs, d.MAPS["full"])
        glyphs = [g for g in read[pairs[locus.id]] if g["char"] != lines.SPACE]
        where, n = recognize.align_to_columns(
            [tokens[g["char"]] for g in glyphs], recognize.consensus([c.readings for c in cols])
        )
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
    args = p.parse_args(argv)
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
        result = page_instances(model, page, inputs, loci, tokens)
        (args.out / f"{page}.json").write_text(json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
