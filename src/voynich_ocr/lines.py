import argparse
import json
import sys
from collections.abc import Iterator
from pathlib import Path

import numpy as np
from PIL import Image

from voynich_ocr import disagreement as d
from voynich_ocr import ivtff, segment, sta
from voynich_ocr.snapshot import RAW, ROOT

OUT = ROOT / "build" / "lines"
# A line image this many times its page's median height holds two text rows (a doubled blla baseline).
TALL = 1.5
# A page whose line widths track its label lengths this weakly has rows paired with the wrong loci.
MIN_PAIRING_R = 0.5
MIN_PAIRING_LINES = 6
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


def single_row(heights: list[int]) -> list[bool]:
    median = float(np.median(heights))
    return [h <= TALL * median for h in heights]


def paired(widths: list[float], lengths: list[int]) -> bool:
    if len(widths) < MIN_PAIRING_LINES:
        return True
    return float(np.corrcoef(widths, lengths)[0, 1]) >= MIN_PAIRING_R


def screen(sizes: list[tuple[int, int]], lengths: list[int]) -> tuple[list[bool], bool]:
    """Which line images are single rows, and whether the kept ones' widths track their label lengths."""
    keep = single_row([h for _, h in sizes])
    kept = [i for i, k in enumerate(keep) if k]
    return keep, paired([sizes[i][0] / sizes[i][1] for i in kept], [lengths[i] for i in kept])


def paper_fill(im: Image.Image) -> Image.Image:
    """The line image with kraken's black polygon fill replaced by the median colour of the rest."""
    a = np.asarray(im.convert("RGB")).copy()
    fill = (a == 0).all(axis=-1)
    a[fill] = np.median(a[~fill], axis=0).astype(np.uint8)
    return Image.fromarray(a)


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


def line_images(page: str, rows: dict[str, dict]) -> Iterator[tuple[str, Image.Image]]:
    """Kraken's straightened, polygon-masked image of each row, by row id."""
    from kraken.containers import BaselineLine, Segmentation
    from kraken.lib.segmentation import extract_polygons

    lines = [BaselineLine(id=k, baseline=r["baseline"], boundary=r["boundary"]) for k, r in rows.items()]
    seg = Segmentation(type="baselines", imagename=str(segment.IMAGES / f"{page}.jpg"), text_direction="horizontal-lr",
                       script_detection=False, lines=lines)
    for im, line in extract_polygons(Image.open(segment.IMAGES / f"{page}.jpg"), seg):
        yield line.id, im


def extract(page: str, rows: dict[str, dict], out: Path, fill: str) -> None:
    for k, im in line_images(page, rows):
        (paper_fill(im) if fill == "paper" else im).save(out / f"{stem(k)}.png")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lines")
    p.add_argument("--seg", type=Path, default=segment.OUT)
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--fill", choices=["black", "paper"], default="black", help="outside the line polygon")
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
        extract(page, {k: rows[k] for k in labelled[page]}, target, args.fill)
        sizes = [Image.open(target / f"{stem(k)}.png").size for k in labelled[page]]
        keep, report[page]["paired"] = screen(sizes, [len(ts) for ts in labelled[page].values()])
        for k, single in zip(list(labelled[page]), keep, strict=True):
            if not single:
                (target / f"{stem(k)}.png").unlink()
                del labelled[page][k]
        if not report[page]["paired"]:
            for k in labelled[page]:
                (target / f"{stem(k)}.png").unlink()
            continue
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
