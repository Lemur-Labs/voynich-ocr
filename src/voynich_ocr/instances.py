import argparse
import json
import sys
from pathlib import Path

from voynich_ocr import disagreement as d
from voynich_ocr import lines, recognize, segment
from voynich_ocr.snapshot import ROOT

OUT = ROOT / "build" / "instances"


def zl_tokens(inputs: d.Inputs, locus: str) -> list[str]:
    return [d.token(g.code, inputs.aaa) for g in inputs.sources["ZL"].loci.get(locus, [])]


def page_instances(model, page: str, inputs: d.Inputs, loci: list[d.Locus], tokens: dict[str, str]) -> dict:
    """Recognized glyphs of one page's paragraph rows, each tied to its map column. Rows pair with loci by count
    when the counts match, else by text (`recognize.assign_by_text`)."""
    rows = segment.page_lines(json.loads((segment.OUT / f"{page}.json").read_text()), segment.height(page))
    heights = [max(p[1] for p in r["boundary"]) - min(p[1] for p in r["boundary"]) for r in rows]
    rows = [r for r, keep in zip(rows, lines.single_row(heights), strict=True) if keep]
    read = recognize.read_page(model, page, rows)
    decoded = [[tokens[g["char"]] for g in row if g["char"] != lines.SPACE] for row in read]
    ids = [lo.id for lo in loci]
    by_count = segment.assign(rows, ids)
    if by_count is not None:
        pairs = {k: i for i, k in enumerate(ids)}
        rule = "count"
    else:
        pairs = recognize.assign_by_text(decoded, {k: zl_tokens(inputs, k) for k in ids})
        rule = "text"
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
