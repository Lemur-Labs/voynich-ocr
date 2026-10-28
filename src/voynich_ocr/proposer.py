import json

import numpy as np
from PIL import Image

# Components smaller than this share of the line height squared are specks, not glyphs.
MIN_AREA = 0.02


def components(line: Image.Image) -> list[tuple[int, int, int, int]]:
    """Label-free glyph proposals: 8-connected ink components of the Otsu-binarized line, left to right, as
    (x0, y0, x1, y1) boxes. Pure black is kraken's fill outside the line polygon, not ink."""
    from skimage.filters import threshold_otsu
    from skimage.measure import label, regionprops

    rgb = np.asarray(line.convert("RGB"))
    inside = rgb.any(axis=2)
    gray = np.asarray(line.convert("L"), dtype=float)
    ink = inside & (gray < threshold_otsu(gray[inside]))
    floor = MIN_AREA * gray.shape[0] ** 2
    boxes = [r.bbox for r in regionprops(label(ink, connectivity=2)) if r.area >= floor]
    return sorted(((b[1], b[0], b[3], b[2]) for b in boxes), key=lambda b: (b[0], b[1]))


def page_control(page: str, pairs: dict[str, int], inputs, by_id: dict) -> tuple[list[Image.Image], list[dict]]:
    """Control-arm crops of one page, from lines whose component count equals their consensus glyph count; each
    crop takes the column of the consensus glyph in the same position."""
    from kraken.containers import BaselineLine, Segmentation
    from kraken.lib.segmentation import extract_polygons

    from voynich_ocr import clusters, lines, recognize, segment
    from voynich_ocr import disagreement as d

    rows = segment.page_lines(json.loads((segment.OUT / f"{page}.json").read_text()), segment.height(page))
    heights = [max(p[1] for p in r["boundary"]) - min(p[1] for p in r["boundary"]) for r in rows]
    rows = [r for r, keep in zip(rows, lines.single_row(heights), strict=True) if keep]
    image = Image.open(segment.IMAGES / f"{page}.jpg")
    baselines = [BaselineLine(id=k, baseline=rows[i]["baseline"], boundary=rows[i]["boundary"]) for k, i in pairs.items()]
    seg = Segmentation(type="baselines", imagename=str(segment.IMAGES / f"{page}.jpg"),
                       text_direction="horizontal-lr", script_detection=False, lines=baselines)  # fmt: skip
    crops, metas = [], []
    for im, line in extract_polygons(image, seg):
        cols, _ = d.locus_columns(by_id[line.id], inputs, d.MAPS["full"])
        cons = recognize.consensus([c.readings for c in cols])
        boxes = components(im)
        if len(boxes) != len(cons):
            continue
        for (x0, y0, x1, y1), (_, k) in zip(boxes, cons, strict=True):
            c = cols[k]
            crops.append(clusters.crop(im, [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]))
            metas.append({
                "page": page, "locus": line.id, "column": k, "class": c.cls, "gated": c.gated,
                "zl": " ".join(c.readings.get("ZL", ())),
                "readings": {s: " ".join(c.readings[s]) for s in c.contributing},
            })  # fmt: skip
    return crops, metas
