from pathlib import Path

import numpy as np

from voynich_ocr import segment
from voynich_ocr.align import majority

BLANK = 0


def spans(probs: np.ndarray) -> list[tuple[int, int, int, float]]:
    """Greedy CTC label runs of a (classes, frames) posterior: (class, first frame, end frame, confidence), where a
    span is a maximal run of frames sharing a non-blank argmax and its confidence is the maximum of that class's
    posterior over the run."""
    best = probs.argmax(axis=0)
    out = []
    start = 0
    for t in range(1, len(best) + 1):
        if t < len(best) and best[t] == best[start]:
            continue
        c = int(best[start])
        if c != BLANK:
            out.append((c, start, t, float(probs[c, start:t].max())))
        start = t
    return out


def regions(runs: list[tuple[int, int, int, float]], n_frames: int) -> list[tuple[float, float]]:
    """Each span's frame range widened to the midpoints of the gaps to its neighbours; the outer spans extend by the
    same margin they get on their inner side."""
    if len(runs) < 2:
        return [(s, e) for _, s, e, _ in runs]
    cuts = [(runs[i][2] + runs[i + 1][1]) / 2 for i in range(len(runs) - 1)]
    lo = [max(0.0, runs[0][1] - (cuts[0] - runs[0][2])), *cuts]
    hi = [*cuts, min(n_frames, runs[-1][2] + (runs[-1][1] - cuts[-1]))]
    return list(zip(lo, hi, strict=True))


def baseline_map(runs: list[tuple[int, int, int, float]], cuts: list) -> tuple[float, float] | None:
    """Slope and offset from output frame to distance along the baseline, fitted to kraken's span positions, which
    take a span's last frame as its end and are clamped to the line's extent."""
    frames = [f for _, s, e, _ in runs for f in (s, e - 1)]
    dists = [x for c in cuts for x in c]
    inner = {(f, x) for f, x in zip(frames, dists, strict=True) if 0 < x < max(dists)}
    if len({f for f, _ in inner}) < 2:
        return None
    a, b = np.polyfit(*zip(*sorted(inner), strict=True), 1)
    return float(a), float(b)


def _distance(a: list[str], b: list[str]) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def _similarity(row: list[str], locus: list[str]) -> float:
    return max(0.0, 1 - _distance(row, locus) / max(len(locus), 1))


def assign_by_text(rows: list[list[str]], loci: dict[str, list[str]]) -> dict[str, int]:
    """Rows to loci in reading order, maximizing summed similarity; a locus takes a row only when they share
    something, and spurious rows (labels, drawings) go unmatched."""
    ids = list(loci)
    n, m = len(ids), len(rows)
    sim = [[_similarity(rows[j], loci[ids[i]]) for j in range(m)] for i in range(n)]
    best = np.zeros((n + 1, m + 1))
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            best[i, j] = max(best[i - 1, j], best[i, j - 1], best[i - 1, j - 1] + sim[i - 1][j - 1])
    out = {}
    i, j = n, m
    while i and j:
        if best[i, j] == best[i - 1, j]:
            i -= 1
        elif best[i, j] == best[i, j - 1]:
            j -= 1
        else:
            if sim[i - 1][j - 1] > 0:
                out[ids[i - 1]] = j - 1
            i, j = i - 1, j - 1
    return dict(sorted(out.items(), key=lambda kv: ids.index(kv[0])))


def consensus(readings: list[dict[str, tuple[str, ...]]]) -> list[tuple[str, int]]:
    """The locus's column-majority string, gaps removed, as (token, column index) pairs."""
    out = []
    for k, r in enumerate(readings):
        for token in majority(list(r.values())):
            out.append((token, k))
    return out


def align_to_columns(recognized: list[str], cons: list[tuple[str, int]]) -> tuple[list[int | None], int]:
    """Each recognized glyph's column under a unit-cost alignment to the consensus; insertions get None."""
    target = [t for t, _ in cons]
    n, m = len(recognized), len(target)
    cost = np.zeros((n + 1, m + 1), dtype=int)
    cost[:, 0] = np.arange(n + 1)
    cost[0, :] = np.arange(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost[i, j] = min(cost[i - 1, j] + 1, cost[i, j - 1] + 1,
                             cost[i - 1, j - 1] + (recognized[i - 1] != target[j - 1]))  # fmt: skip
    out: list[int | None] = [None] * n
    i, j = n, m
    while i and j:
        if cost[i, j] == cost[i - 1, j - 1] + (recognized[i - 1] != target[j - 1]):
            out[i - 1] = cons[j - 1][1]
            i, j = i - 1, j - 1
        elif cost[i, j] == cost[i - 1, j] + 1:
            i -= 1
        else:
            j -= 1
    return out, sum(c is None for c in out)


def load(path: Path):
    from kraken.tasks import RecognitionTaskModel

    return RecognitionTaskModel.load_model(path)


def log_posteriors(probs: np.ndarray, temperature: float) -> np.ndarray:
    """log_softmax(log p / T) over classes: kraken's posteriors are softmax(logits), so this is softmax(logits / T)."""
    with np.errstate(divide="ignore"):
        z = np.log(probs.astype(np.float64)) / temperature
    top = z.max(axis=0)
    return z - (top + np.log(np.exp(z - top).sum(axis=0)))


def _records(model, page: str, rows: list[dict], temperature: float = 1.0):
    from kraken.configs import RecognitionInferenceConfig
    from kraken.containers import BaselineLine, Segmentation
    from PIL import Image

    seg = Segmentation(
        type="baselines",
        imagename=str(segment.IMAGES / f"{page}.jpg"),
        text_direction="horizontal-lr",
        script_detection=False,
        lines=[BaselineLine(id=str(i), baseline=r["baseline"], boundary=r["boundary"]) for i, r in enumerate(rows)],
    )
    config = RecognitionInferenceConfig(
        return_logits=True, temperature=temperature, accelerator="cpu", num_workers=0, bidi_reordering=False
    )
    return model.predict(Image.open(segment.IMAGES / f"{page}.jpg"), seg, config)


def posteriors(model, page: str, rows: list[dict]) -> list[np.ndarray]:
    """Each row's (classes, frames) posteriors at temperature 1; kraken 7.1.1's `logits` are softmax outputs."""
    return [rec.logits.numpy() for rec in _records(model, page, rows)]


def read_page(model, page: str, rows: list[dict], temperature: float = 1.0) -> list[list[dict]]:
    """Each row's glyphs as {char, confidence, cut}; `cut` is the line polygon between the span's `regions`
    boundaries, or kraken's own cut for the span when the row is too short to map frames onto the baseline."""
    from kraken.lib.segmentation import compute_polygon_section

    l2c = model.net.codec.l2c
    out = []
    for rec in _records(model, page, rows, temperature):
        probs = rec.logits.numpy()
        runs = spans(probs)
        if len(runs) != len(rec.cuts):
            raise AssertionError(f"{page}: {len(runs)} spans but {len(rec.cuts)} cuts")
        # kraken 7.1.1 keeps span positions along the baseline in the private `_cuts`.
        fit = baseline_map(runs, rec._cuts) if runs else None
        if fit is None:
            cuts = list(rec.cuts)
        else:
            a, b = fit
            length = rec._bl_length
            cuts = [
                compute_polygon_section(
                    rec.baseline, rec.boundary, min(max(a * lo + b, 0), length), min(max(a * hi + b, 0), length)
                )
                for lo, hi in regions(runs, probs.shape[1])
            ]
        out.append(
            [
                {"char": l2c[(c,)], "confidence": conf, "cut": [list(map(float, p)) for p in cut]}
                for (c, _, _, conf), cut in zip(runs, cuts, strict=True)
            ]
        )
    return out
