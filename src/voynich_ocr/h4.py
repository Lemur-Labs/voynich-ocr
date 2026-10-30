import argparse
import itertools
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

from voynich_ocr import disagreement as d
from voynich_ocr import freeze, g3, lines, naibbe, recognize, scoring, segment, sta
from voynich_ocr.instances import OUT as INSTANCES
from voynich_ocr.snapshot import RAW, ROOT

SEED = 20261027
STREAMS = ("exemplar", "level", "band", "disputed", "bootstrap", "spacing")
BOOTSTRAP_CHILDREN = ("R1", "level 0", "level 1", "level 2", "R2")
WORDS_PER_LINE = 9
LINES = 600
# (σ as a share of the box height, fade a, occluded share f of the box width), per A7.
LEVELS = ((0.0, 1.0, 0.0), (0.03, 0.6, 0.2), (0.06, 0.35, 0.4))
MARGIN = 8
BASELINE = 8
WORD_SPACES = (".", "-")
OUT = ROOT / "results" / "g4"
BUILD = ROOT / "build" / "g4"


@dataclass(frozen=True)
class Exemplar:
    page: str
    locus: str
    column: int
    order: int
    cut: tuple

    @property
    def key(self) -> str:
        return f"{self.page}/{self.locus}/{self.column}/{self.order}"

    def box(self, width: int, height: int) -> tuple[int, int, int, int]:
        """The bounding box `clusters.crop` takes before padding."""
        xs, ys = [p[0] for p in self.cut], [p[1] for p in self.cut]
        return (max(0, int(min(xs))), max(0, int(min(ys))), min(width, int(max(xs)) + 1), min(height, int(max(ys)) + 1))


def background(box: np.ndarray) -> np.ndarray:
    return np.percentile(box.reshape(-1, box.shape[2]).astype(np.float64), 90, axis=0)


def degrade(box: np.ndarray, level: int, u: float) -> np.ndarray:
    """A7's operator: fade, blur, occlude, then one clip and round to uint8."""
    share, a, f = LEVELS[level]
    height, width = box.shape[:2]
    b = background(box)
    x = b + a * (box.astype(np.float64) - b)
    if share:
        sigma = share * height
        x = gaussian_filter(x, sigma=(sigma, sigma, 0), truncate=4.0, mode="nearest")
    w = int(np.rint(f * width))
    if w:
        left = int(np.floor(u * (width - w + 1)))
        x[:, left : left + w] = b
    return np.rint(np.clip(x, 0, 255)).astype(np.uint8)


def collage(words: list[list[np.ndarray]], spaces: list[int], fill: np.ndarray) -> tuple[Image.Image, list]:
    """Boxes left to right with bottoms aligned, `spaces[i]` pixels after word i, on a canvas of `fill` with a
    MARGIN on every side; returns the image and the line's baseline."""
    boxes = [b for w in words for b in w]
    height = max(b.shape[0] for b in boxes) + 2 * MARGIN
    width = sum(b.shape[1] for b in boxes) + sum(spaces) + 2 * MARGIN
    canvas = np.empty((height, width, 3), dtype=np.uint8)
    canvas[:] = np.rint(fill).astype(np.uint8)
    x = MARGIN
    for i, word in enumerate(words):
        for b in word:
            canvas[height - MARGIN - b.shape[0] : height - MARGIN, x : x + b.shape[1]] = b
            x += b.shape[1]
        if i < len(spaces):
            x += spaces[i]
    return Image.fromarray(canvas), [[0, height - BASELINE], [width - 1, height - BASELINE]]


def draw(u: float, n: int) -> int:
    return int(np.floor(u * n))


def streams(seed: int = SEED) -> dict[str, np.random.Generator]:
    children = np.random.SeedSequence(seed).spawn(len(STREAMS))
    return {name: np.random.default_rng(c) for name, c in zip(STREAMS, children, strict=True)}


def bootstrap_seeds(seed: int = SEED) -> dict[str, np.random.SeedSequence]:
    root = np.random.SeedSequence(seed).spawn(len(STREAMS))[STREAMS.index("bootstrap")]
    return dict(zip(BOOTSTRAP_CHILDREN, root.spawn(len(BOOTSTRAP_CHILDREN)), strict=True))


def bitrans() -> Path:
    exe = BUILD / "bitrans"
    if not exe.exists():
        exe.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["cc", "-O2", "-o", str(exe), str(RAW / "bitrans" / "bitrans.c")], check=True,
                       capture_output=True)  # fmt: skip
    return exe


def eva_tokens(words: list[str], aaa: dict[str, str]) -> list[list[str]]:
    """Each EVA word as aaa tokens, through STA by the pinned bitrans rules."""
    out = subprocess.run(
        [str(bitrans()), "-2", "-m2", "-f", str(RAW / "bitrans" / "STA-Eva_def.bit")],
        input="\n".join(words) + "\n", capture_output=True, text=True, check=True,
    ).stdout.split("\n")[: len(words)]  # fmt: skip
    return [[aaa[g.code] for g in sta.glyphs(w)] for w in out]


def text(aaa: dict[str, str]) -> list[list[list[str]]]:
    """The first LINES lines of WORDS_PER_LINE enciphered words, each word as aaa tokens."""
    cipher, _ = naibbe.encipher(naibbe.PLAINTEXT.read_text(encoding="utf-8").split("\n"), SEED)
    words = [w for line in cipher for w in line.split()][: LINES * WORDS_PER_LINE]
    if len(words) < LINES * WORDS_PER_LINE:
        raise SystemExit(f"{len(words)} enciphered words; A7 needs {LINES * WORDS_PER_LINE}")
    tokens = eva_tokens(words, aaa)
    return [tokens[i : i + WORDS_PER_LINE] for i in range(0, len(tokens), WORDS_PER_LINE)]


def _instances(instances_dir: Path, pages: list[str]):
    for page in sorted(pages):
        f = instances_dir / f"{page}.json"
        if f.exists():
            for i, m in enumerate(json.loads(f.read_text())["instances"]):
                yield Exemplar(page, m["locus"], m["column"], i, tuple(map(tuple, m["cut"]))), m


def _ordered(pools: dict[str, list[Exemplar]]) -> dict[str, list[Exemplar]]:
    return {t: sorted(v, key=lambda e: (e.page, e.locus, e.column, e.order)) for t, v in pools.items()}


def exemplar_pool(instances_dir: Path, pages: list[str]) -> dict[str, list[Exemplar]]:
    """A4: instances whose recognized token equals the ZL reading of their column."""
    pools: dict[str, list[Exemplar]] = {}
    for e, m in _instances(instances_dir, pages):
        if m["token"] == m["zl"]:
            pools.setdefault(m["token"], []).append(e)
    return _ordered(pools)


def disputed_pool(instances_dir: Path, pages: list[str], codec: set[str]) -> dict[str, list[Exemplar]]:
    """A7: instances in gated disagree columns whose ZL reading is one codec token, labelled by that token."""
    pools: dict[str, list[Exemplar]] = {}
    for e, m in _instances(instances_dir, pages):
        z = m["zl"]
        if m["gated"] and m["class"] == "disagree" and z and " " not in z and z in codec:
            pools.setdefault(z, []).append(e)
    return _ordered(pools)


def gap_pool(instances_dir: Path, pages: list[str], inputs: d.Inputs) -> list[int]:
    """A7: horizontal distance between the cut boxes either side of a ZL word space on one row, negatives as 0."""
    by_id = {lo.id: lo for lo in inputs.loci}
    found = []
    for page in sorted(pages):
        f = instances_dir / f"{page}.json"
        if not f.exists():
            continue
        rows: dict[str, list[dict]] = {}
        for m in json.loads(f.read_text())["instances"]:
            rows.setdefault(m["locus"], []).append(m)
        for locus, row in rows.items():
            spaced = _zl_spaced_columns(by_id[locus], inputs)
            for left, right in itertools.pairwise(row):
                if left["column"] < right["column"] and spaced & set(range(left["column"], right["column"])):
                    gap = min(p[0] for p in right["cut"]) - max(p[0] for p in left["cut"])
                    found.append(((page, locus, left["column"]), max(0, int(np.rint(gap)))))
    return [g for _, g in sorted(found, key=lambda x: x[0])]


def _zl_spaced_columns(locus: d.Locus, inputs: d.Inputs) -> set[int]:
    """Full-map columns whose last ZL glyph is followed by a word space."""
    columns, _ = d.locus_columns(locus, inputs, d.ORDER)
    glyphs = inputs.sources["ZL"].loci.get(locus.id, [])
    spaced, at = set(), 0
    for c in columns:
        at += len(c.readings.get("ZL", ()))
        if c.readings.get("ZL") and at < len(glyphs) and glyphs[at - 1].space_after in WORD_SPACES:
            spaced.add(c.index)
    return spaced


def plan(text_lines, exemplars, disputed, gaps) -> dict:
    """Every random draw, in A7's order: each stream in line order, then glyph (or word-space) order."""
    rng = streams()
    out = {"R0": [], "R1": [], "R2": [], "gaps": 0}
    for line in text_lines:
        r0, r1, r2, spacing = [], [], [], []
        for w, word in enumerate(line):
            w0, w1, w2 = [], [], []
            for t in word:
                pool = exemplars.get(t, [])
                u_ex, u_level, u_band, u_dis = (rng[s].random() for s in ("exemplar", "level", "band", "disputed"))
                ex = pool[draw(u_ex, len(pool))] if pool else None
                level = draw(u_level, len(LEVELS))
                dpool = disputed.get(t, [])
                dex = dpool[draw(u_dis, len(dpool))] if dpool else None
                if ex is None:
                    out["gaps"] += 1
                    continue
                w0.append({"token": t, "exemplar": ex, "level": 0, "u": u_band})
                w1.append({"token": t, "exemplar": ex, "level": level, "u": u_band})
                w2.append({"token": t, "exemplar": dex or ex, "level": 0, "u": u_band, "disputed": dex is not None})
            r0.append(w0)
            r1.append(w1)
            r2.append(w2)
            if w < len(line) - 1:
                spacing.append(gaps[draw(rng["spacing"].random(), len(gaps))])
        out["R0"].append({"words": r0})
        out["R1"].append({"words": r1})
        out["R2"].append({"words": r2, "spaces": spacing})
    return out


def _crops(planned: dict) -> dict[str, np.ndarray]:
    """Each needed exemplar's box, reading every page image once."""
    needed: dict[str, dict[str, Exemplar]] = {}
    for name in ("R0", "R1", "R2"):
        for line in planned[name]:
            for word in line["words"]:
                for g in word:
                    needed.setdefault(g["exemplar"].page, {})[g["exemplar"].key] = g["exemplar"]
    boxes = {}
    for page, exs in sorted(needed.items()):
        im = Image.open(segment.IMAGES / f"{page}.jpg").convert("RGB")
        for key, e in exs.items():
            boxes[key] = np.asarray(im.crop(e.box(im.width, im.height)))
    return boxes


def render(line: dict, boxes: dict[str, np.ndarray]) -> tuple[Image.Image, list]:
    words = [[degrade(boxes[g["exemplar"].key], g["level"], g["u"]) for g in w] for w in line["words"]]
    flat = [boxes[g["exemplar"].key] for w in line["words"] for g in w]
    fill = np.median([background(b) for b in flat], axis=0)
    spaces = line.get("spaces") or [int(np.rint(np.median([b.shape[1] for b in flat])))] * (len(words) - 1)
    return collage(words, spaces, fill)


def read_image(model, image: Image.Image, baseline: list) -> np.ndarray:
    from kraken.configs import RecognitionInferenceConfig
    from kraken.containers import BaselineLine, Segmentation

    w, h = image.size
    boundary = [[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]]
    seg = Segmentation(type="baselines", imagename="h4", text_direction="horizontal-lr", script_detection=False,
                       lines=[BaselineLine(id="0", baseline=baseline, boundary=boundary)])  # fmt: skip
    config = RecognitionInferenceConfig(return_logits=True, accelerator="cpu", num_workers=0, bidi_reordering=False)
    (rec,) = list(model.predict(image, seg, config))
    return rec.logits.numpy()


def alignment(recognized: list[str], reference: list[str]) -> list[tuple[int | None, int | None]]:
    """Unit-cost edit alignment as (recognized index, reference index) pairs; ties prefer the diagonal, then a
    deletion, then an insertion."""
    n, m = len(recognized), len(reference)
    cost = np.zeros((n + 1, m + 1), dtype=int)
    cost[:, 0] = np.arange(n + 1)
    cost[0, :] = np.arange(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sub = cost[i - 1, j - 1] + (recognized[i - 1] != reference[j - 1])
            cost[i, j] = min(sub, cost[i, j - 1] + 1, cost[i - 1, j] + 1)
    pairs, i, j = [], n, m
    while i or j:
        if i and j and cost[i, j] == cost[i - 1, j - 1] + (recognized[i - 1] != reference[j - 1]):
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif j and cost[i, j] == cost[i, j - 1] + 1:
            pairs.append((None, j - 1))
            j -= 1
        else:
            pairs.append((i - 1, None))
            i -= 1
    return pairs[::-1]


def score_line(row: list[dict], glyphs: list[dict]) -> dict:
    """`row` is the rendered glyphs in order; `glyphs` the recognized ones, spaces removed."""
    pairs = alignment([g["token"] for g in glyphs], [g["token"] for g in row])
    scored, deleted = [], []
    for r, k in pairs:
        if r is None:
            deleted.append(row[k])
        elif k is None:
            scored.append({"confidence": glyphs[r]["confidence"], "correct": False, "inserted": True})
        else:
            scored.append({"confidence": glyphs[r]["confidence"], "correct": glyphs[r]["token"] == row[k]["token"],
                           "inserted": False, "level": row[k]["level"], "disputed": row[k].get("disputed", False),
                           "source": row[k]["exemplar"].key})  # fmt: skip
    return {"scored": scored, "deleted": deleted,
            "distance": recognize._distance([g["token"] for g in glyphs], [g["token"] for g in row]),
            "length": len(row)}  # fmt: skip


def _ece(metas: list[dict], groups: list, seed) -> dict:
    conf = np.array([m["confidence"] for m in metas], dtype=float)
    correct = np.array([m["correct"] for m in metas], dtype=float)
    iv = scoring.page_bootstrap(lambda idx: scoring.ece(conf[idx], correct[idx], g3.ECE_BINS), np.array(groups),
                                seed=seed)  # fmt: skip
    return {"point": iv.point, "lo": iv.lo, "hi": iv.hi, "n": len(metas), "accuracy": float(correct.mean())}


def reliability(metas: list[dict]) -> list[dict]:
    conf = np.array([m["confidence"] for m in metas], dtype=float)
    correct = np.array([m["correct"] for m in metas], dtype=float)
    edges = np.linspace(0.0, 1.0, g3.ECE_BINS + 1)
    idx = np.clip(np.digitize(conf, edges[1:-1], right=True), 0, g3.ECE_BINS - 1)
    return [{"bin": b, "n": int((idx == b).sum()), "confidence": float(conf[idx == b].mean()),
             "accuracy": float(correct[idx == b].mean())} for b in range(g3.ECE_BINS) if (idx == b).any()]  # fmt: skip


def summarize(scored: dict[str, list[dict]]) -> dict:
    """A7's statistics from each rendering's scored lines."""
    seeds = bootstrap_seeds()
    out: dict = {}
    for name in ("R0", "R1"):
        lines_ = scored[name]
        out[name] = {"cer": sum(s["distance"] for s in lines_) / sum(s["length"] for s in lines_),
                     "deleted": sum(len(s["deleted"]) for s in lines_)}  # fmt: skip
    r1 = [(i, m) for i, s in enumerate(scored["R1"]) for m in s["scored"]]
    out["R1"]["ece"] = _ece([m for _, m in r1], [i for i, _ in r1], seeds["R1"])
    out["R1"]["reliability"] = reliability([m for _, m in r1])
    out["R1"]["levels"] = {}
    for level in range(len(LEVELS)):
        at = [(i, m) for i, m in r1 if not m["inserted"] and m["level"] == level]
        deleted = sum(1 for s in scored["R1"] for g in s["deleted"] if g["level"] == level)
        out["R1"]["levels"][str(level)] = {**_ece([m for _, m in at], [i for i, _ in at], seeds[f"level {level}"]),
                                           "deleted": deleted, "reliability": reliability([m for _, m in at])}  # fmt: skip
    rows = [out["R1"]["ece"]] + list(out["R1"]["levels"].values())
    out["calibrated_on_synthetic_ink"] = all(r["hi"] <= 0.05 for r in rows)
    r2 = [m for s in scored["R2"] for m in s["scored"] if not m["inserted"] and m["disputed"]]
    out["R2"] = {**_ece(r2, [m["source"] for m in r2], seeds["R2"]), "instances": len({m["source"] for m in r2}),
                 "reliability": reliability(r2)} if r2 else {"n": 0}  # fmt: skip
    return out


def run(model_path: Path, out: Path, text_lines: list, gate: bool) -> dict:
    if gate:
        freeze.require(model_path)
    split = json.loads(d.SPLITS.read_text())
    test = set(split["test"])
    pages = sorted({p.stem for p in INSTANCES.glob("*.json")} - test)
    table = json.loads((lines.OUT / "codec.json").read_text())
    inputs = d.load()
    exemplars = exemplar_pool(INSTANCES, pages)
    disputed = disputed_pool(INSTANCES, split["validation"], set(table))
    gaps = gap_pool(INSTANCES, split["validation"], inputs)
    planned = plan(text_lines, exemplars, disputed, gaps)
    boxes = _crops(planned)
    temperature = json.loads(g3.TEMPERATURE.read_text())["temperature"]
    model = recognize.load(model_path)
    l2c = model.net.codec.l2c
    chars = {ch: t for t, ch in table.items()}
    out.mkdir(parents=True, exist_ok=True)
    result = out / "result.json"
    with result.open("x") as fh:
        scored: dict[str, list[dict]] = {}
        for name in ("R0", "R1", "R2"):
            (out / name).mkdir(exist_ok=True)
            scored[name] = []
            for i, line in enumerate(planned[name]):
                image, baseline = render(line, boxes)
                image.save(out / name / f"{i:03d}.png")
                row = [g for w in line["words"] for g in w]
                read = g3.glyphs(read_image(model, image, baseline), temperature, l2c)
                glyphs = [{**g, "token": chars[g["char"]]} for g in read if g["char"] != lines.SPACE]
                scored[name].append(score_line(row, glyphs))
        summary = {"lines": len(text_lines), "glyphs": sum(len(w) for line in planned["R0"] for w in line["words"]),
                   "gaps": planned["gaps"], "temperature": temperature,
                   "pools": {"exemplar_tokens": len(exemplars), "disputed_tokens": len(disputed),
                             "disputed_instances": sum(map(len, disputed.values())), "word_gaps": len(gaps)},
                   **summarize(scored)}  # fmt: skip
        fh.write(json.dumps(summary, indent=1) + "\n")
    return summary


def smoke_text(aaa: dict[str, str], lines_: int = 3) -> list:
    """Not Naibbe text: a few lines of seeded random codec tokens, for checking the pipeline end to end."""
    rng = np.random.default_rng(1)
    tokens = sorted(set(aaa.values()))
    return [[[tokens[k] for k in rng.integers(0, len(tokens), 4)] for _ in range(WORDS_PER_LINE)]
            for _ in range(lines_)]  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="h4")
    p.add_argument("model", type=Path, nargs="?", default=freeze.MODEL)
    p.add_argument("--gate", action="store_true", help="the one G4 run: Naibbe text into results/g4")
    p.add_argument("--smoke", type=Path, help="seeded non-Naibbe text into this directory under build/")
    args = p.parse_args(argv)
    if args.gate == bool(args.smoke):
        p.error("give exactly one of --gate and --smoke DIR")
    aaa = sta.load_aaa((RAW / "bitrans" / "STA-aaa.bit").read_text())
    if args.gate:
        print(json.dumps(run(args.model, OUT, text(aaa), gate=True)))
        return 0
    if (ROOT / "build") not in args.smoke.resolve().parents:
        p.error("--smoke writes under build/ only")
    print(json.dumps(run(args.model, args.smoke, smoke_text(aaa), gate=False)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
