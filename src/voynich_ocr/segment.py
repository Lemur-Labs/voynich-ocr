import argparse
import json
import statistics
import sys
from itertools import pairwise
from pathlib import Path

from shapely.geometry import MultiPoint

from voynich_ocr.disagreement import test_pages
from voynich_ocr.snapshot import RAW, ROOT

IMAGES = RAW / "images"
OUT = ROOT / "build" / "seg"
# Post-filter: lines wholly in the top BAND of the page (folio numbers) are dropped; fragments of one row merge when
# the next starts within MERGE_DY row spacings of where the previous ends and overlaps it by at most MERGE_OVERLAP px;
# rows shorter than SHORT of the widest are dropped.
BAND = 0.06
MERGE_DY = 0.5
MERGE_OVERLAP = 40
SHORT = 0.15


def height(page: str) -> int:
    from PIL import Image

    return Image.open(IMAGES / f"{page}.jpg").size[1]


def image_pages() -> list[str]:
    return sorted(p.stem for p in IMAGES.glob("f*.jpg"))


def segment(model, page: str) -> list[dict]:
    """blla lines of one page, as baselines and boundary polygons in image pixels, in kraken's reading order."""
    from kraken.configs import SegmentationInferenceConfig
    from PIL import Image

    seg = model.predict(Image.open(IMAGES / f"{page}.jpg"), SegmentationInferenceConfig(accelerator="cpu"))
    return [{"baseline": line.baseline, "boundary": line.boundary} for line in seg.lines]


def _x0(line: dict) -> float:
    return line["baseline"][0][0]


def _x1(line: dict) -> float:
    return line["baseline"][-1][0]


def _ymid(line: dict) -> float:
    ys = [p[1] for p in line["baseline"]]
    return (min(ys) + max(ys)) / 2


def _spacing(lines: list[dict]) -> float:
    widest = max(_x1(l) - _x0(l) for l in lines)
    ys = sorted(_ymid(l) for l in lines if _x1(l) - _x0(l) >= widest / 2)
    gaps = [b - a for a, b in pairwise(ys)]
    return statistics.median(gaps) if gaps else float("inf")


def _merge(a: dict, b: dict) -> dict:
    hull = MultiPoint([tuple(p) for p in a["boundary"] + b["boundary"]]).convex_hull
    return {"baseline": a["baseline"] + b["baseline"], "boundary": [list(p) for p in hull.exterior.coords[:-1]]}


def page_lines(lines: list[dict], height: int) -> list[dict]:
    """blla lines after the post-filter, one per text row, top to bottom."""
    lines = [l for l in lines if _x1(l) > _x0(l) and max(p[1] for p in l["baseline"]) > BAND * height]
    if not lines:
        return []
    limit = MERGE_DY * _spacing(lines)
    rows: list[dict] = []
    for line in sorted(lines, key=_x0):
        start = line["baseline"][0][1]
        near = [
            r
            for r in rows
            if _x0(line) >= _x1(r) - MERGE_OVERLAP and abs(start - r["baseline"][-1][1]) < limit
        ]
        if near:
            best = min(near, key=lambda r: abs(start - r["baseline"][-1][1]))
            rows[rows.index(best)] = _merge(best, line)
        else:
            rows.append(line)
    widest = max(_x1(r) - _x0(r) for r in rows)
    return sorted((r for r in rows if _x1(r) - _x0(r) >= SHORT * widest), key=_ymid)


def assign(rows: list[dict], loci: list[str]) -> dict[str, dict] | None:
    """Rows to paragraph loci in order; None when the counts differ, which excludes the page."""
    if len(rows) != len(loci):
        return None
    return dict(zip(loci, rows, strict=True))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="segment")
    p.add_argument("pages", nargs="*", help="default: every non-test page with an image")
    p.add_argument("--test", action="store_true", help="also segment test pages (only once configs are frozen)")
    p.add_argument("--out", type=Path, default=OUT)
    args = p.parse_args(argv)
    test = test_pages()
    if not args.test and (blocked := sorted(set(args.pages) & test)):
        raise SystemExit(f"test pages need --test: {blocked}")
    pages = [p for p in args.pages or image_pages() if args.test or p not in test]
    from kraken.tasks import SegmentationTaskModel

    model = SegmentationTaskModel.load_model()
    args.out.mkdir(parents=True, exist_ok=True)
    for page in pages:
        dest = args.out / f"{page}.json"
        if not dest.exists():
            dest.write_text(json.dumps(segment(model, page)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
