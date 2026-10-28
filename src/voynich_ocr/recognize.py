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


def read_page(model, page: str, rows: list[dict], temperature: float = 1.0) -> list[list[dict]]:
    """Each row's glyphs as {char, confidence, cut}; `cut` is kraken's polygon for the same greedy label run."""
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
    l2c = model.net.codec.l2c
    out = []
    for rec in model.predict(Image.open(segment.IMAGES / f"{page}.jpg"), seg, config):
        runs = spans(rec.logits.numpy())
        if len(runs) != len(rec.cuts):
            raise AssertionError(f"{page}: {len(runs)} spans but {len(rec.cuts)} cuts")
        out.append(
            [
                {"char": l2c[(c,)], "confidence": conf, "cut": [list(map(float, p)) for p in cut]}
                for (c, _, _, conf), cut in zip(runs, rec.cuts, strict=True)
            ]
        )
    return out
