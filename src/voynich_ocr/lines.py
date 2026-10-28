import argparse
import json
import sys
from pathlib import Path

import numpy as np

from voynich_ocr import disagreement as d
from voynich_ocr import ivtff, segment, sta
from voynich_ocr.snapshot import RAW, ROOT

OUT = ROOT / "build" / "lines"
EARLY_STOPPING_SHARE = 0.1
EARLY_STOPPING_SEED = 20261027
SPACE = " "


def codec(tokens: list[str]) -> dict[str, str]:
    return {t: chr(0xE000 + i) for i, t in enumerate(sorted(set(tokens)))}


def tokens(glyphs: list[sta.Glyph], aaa: dict[str, str]) -> list[str] | None:
    """ZL's reading of one line as aaa tokens with word spaces; None when it has a `?`, which no label can carry."""
    out = []
    for i, g in enumerate(glyphs):
        if g.code == sta.UNKNOWN:
            return None
        out.append(aaa[g.code])
        if g.space_after and i < len(glyphs) - 1:
            out.append(SPACE)
    return out


def early_stopping_pages(pages: list[str]) -> list[str]:
    pages = sorted(pages)
    rng = np.random.default_rng(EARLY_STOPPING_SEED)
    n = round(EARLY_STOPPING_SHARE * len(pages))
    return sorted(rng.choice(pages, size=n, replace=False).tolist())


def paragraph_loci() -> dict[str, list[str]]:
    zl = ivtff.parse((RAW / d.STA_FILES["ZL"]).read_text())
    out: dict[str, list[str]] = {}
    for lo in zl.loci:
        if lo.exists and lo.type.startswith("P"):
            out.setdefault(lo.page, []).append(lo.id)
    return out


def stem(locus: str) -> str:
    """File stem for a locus; kraken strips every suffix to find the label file, so no dots."""
    return locus.replace(".", "_")


def extract(page: str, rows: dict[str, dict], out: Path) -> None:
    from kraken.containers import BaselineLine, Segmentation
    from kraken.lib.segmentation import extract_polygons
    from PIL import Image

    lines = [BaselineLine(id=k, baseline=r["baseline"], boundary=r["boundary"]) for k, r in rows.items()]
    seg = Segmentation(type="baselines", imagename=str(segment.IMAGES / f"{page}.jpg"), text_direction="horizontal-lr",
                       script_detection=False, lines=lines)
    for im, line in extract_polygons(Image.open(segment.IMAGES / f"{page}.jpg"), seg):
        im.save(out / f"{stem(line.id)}.png")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lines")
    p.add_argument("--seg", type=Path, default=segment.OUT)
    p.add_argument("--out", type=Path, default=OUT)
    args = p.parse_args(argv)
    inputs = d.load()
    zl = inputs.sources["ZL"].loci
    split = json.loads(d.SPLITS.read_text())
    excluded = set(split["test"]) | set(split["validation"])
    loci = paragraph_loci()
    pages, report = {}, {}
    for f in sorted(args.seg.glob("*.json")):
        page = f.stem
        if page in excluded:
            continue
        rows = segment.assign(segment.page_lines(json.loads(f.read_text()), segment.height(page)), loci.get(page, []))
        report[page] = {"loci": len(loci.get(page, [])), "kept": rows is not None}
        if rows:
            pages[page] = rows
    labelled = {
        page: {k: t for k in rows if (t := tokens(zl.get(k, []), inputs.aaa))}
        for page, rows in pages.items()
    }
    table = codec([t for page in labelled.values() for ts in page.values() for t in ts if t != SPACE])
    table[SPACE] = SPACE
    held = set(early_stopping_pages(sorted(labelled)))
    args.out.mkdir(parents=True, exist_ok=True)
    manifests: dict[str, list[str]] = {"train": [], "eval": []}
    for page, rows in pages.items():
        target = args.out / page
        target.mkdir(exist_ok=True)
        extract(page, {k: rows[k] for k in labelled[page]}, target)
        for k, ts in labelled[page].items():
            (target / f"{stem(k)}.gt.txt").write_text("".join(table[t] for t in ts) + "\n")
            manifests["eval" if page in held else "train"].append(str((target / f"{stem(k)}.png").relative_to(ROOT)))
    for name, paths in manifests.items():
        (args.out / f"{name}.txt").write_text("\n".join(paths) + "\n")
    (args.out / "codec.json").write_text(json.dumps(table, ensure_ascii=False, indent=1) + "\n")
    (args.out / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
