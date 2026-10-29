import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from voynich_ocr import disagreement as d
from voynich_ocr import freeze, lines, segment
from voynich_ocr.instances import OUT as INSTANCES
from voynich_ocr.snapshot import RAW, ROOT

OUT = ROOT / "build" / "clusters"
WEIGHTS = RAW / "models" / "vit_small_patch14_dinov2.lvd142m.safetensors"
CROP = 224
HOG_SIZE = 64
K_PER_TOKEN = 2
KMEANS_SEED = 20261027
KMEANS_INIT = 10
BATCH = 64
MEAN = np.array([0.485, 0.456, 0.406])
STD = np.array([0.229, 0.224, 0.225])


def crop(page: Image.Image, cut: list[list[float]]) -> Image.Image:
    """The cut's bounding box, padded to a square with the median colour of the box's border, resized to CROP."""
    xs, ys = [p[0] for p in cut], [p[1] for p in cut]
    box = (max(0, int(min(xs))), max(0, int(min(ys))), min(page.width, int(max(xs)) + 1), min(page.height, int(max(ys)) + 1))
    im = np.asarray(page.crop(box).convert("RGB"))
    border = np.concatenate([im[0], im[-1], im[:, 0], im[:, -1]])
    side = max(im.shape[:2])
    square = np.empty((side, side, 3), dtype=np.uint8)
    square[:] = np.median(border, axis=0).astype(np.uint8)
    top, left = (side - im.shape[0]) // 2, (side - im.shape[1]) // 2
    square[top : top + im.shape[0], left : left + im.shape[1]] = im
    return Image.fromarray(square).resize((CROP, CROP), Image.Resampling.BILINEAR)


def _unit(x: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.where(norm == 0, 1, norm)


def hog(crops: list[Image.Image]) -> np.ndarray:
    from skimage.feature import hog as skhog

    if not crops:
        return np.empty((0, 9 * 4 * (HOG_SIZE // 8 - 1) ** 2))  # orientations, cells per block, blocks
    return _unit(np.stack([
        skhog(np.asarray(c.convert("L").resize((HOG_SIZE, HOG_SIZE), Image.Resampling.BILINEAR)) / 255.0,
              orientations=9, pixels_per_cell=(8, 8), cells_per_block=(2, 2))
        for c in crops
    ]))  # fmt: skip


def dinov2():
    import timm
    import torch
    from safetensors.torch import load_file
    from timm.models.vision_transformer import checkpoint_filter_fn

    model = timm.create_model("vit_small_patch14_dinov2.lvd142m", pretrained=False, img_size=CROP, num_classes=0)
    model.load_state_dict(checkpoint_filter_fn(load_file(WEIGHTS), model))
    torch.set_grad_enabled(False)
    return model.eval()


def embed(model, crops: list[Image.Image]) -> np.ndarray:
    import torch

    if not crops:
        return np.empty((0, model.num_features), dtype=np.float32)
    out = []
    for i in range(0, len(crops), BATCH):
        x = np.stack([(np.asarray(c, dtype=np.float32) / 255.0 - MEAN) / STD for c in crops[i : i + BATCH]])
        out.append(model(torch.from_numpy(x.transpose(0, 3, 1, 2)).float()).numpy())
    return _unit(np.concatenate(out))


def page_features(model, page: str, instances: list[dict]) -> dict[str, np.ndarray]:
    image = Image.open(segment.IMAGES / f"{page}.jpg")
    crops = [crop(image, g["cut"]) for g in instances]
    return {"dinov2": embed(model, crops), "hog": hog(crops)}


def k(root: Path = lines.OUT) -> int:
    """K_PER_TOKEN times the distinct tokens in the training-page labels (train and early-stopping sets)."""
    chars = set()
    for manifest in ("train.txt", "eval.txt"):
        for line in (root / manifest).read_text().split():
            chars |= set((ROOT / line).with_suffix(".gt.txt").read_text().strip())
    return K_PER_TOKEN * len(chars - {lines.SPACE})


def fit(features: np.ndarray, n_clusters: int):
    from sklearn.cluster import KMeans

    # In float32, BLAS rounding noise flips which restart has the lowest inertia, so refits relabel.
    return KMeans(n_clusters=n_clusters, random_state=KMEANS_SEED, n_init=KMEANS_INIT).fit(features.astype(np.float64))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="clusters")
    p.add_argument("--test", action="store_true", help="also featurize test pages (only once configs are frozen)")
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--instances", type=Path, default=INSTANCES)
    args = p.parse_args(argv)
    if args.instances != INSTANCES and args.out == OUT:
        raise SystemExit("features of other instances need their own --out")
    if args.test:
        freeze.require()
    test = d.test_pages()
    (args.out / "features").mkdir(parents=True, exist_ok=True)
    model = dinov2()
    for f in sorted(args.instances.glob("*.json")):
        if f.stem in test and not args.test:
            continue
        dest = args.out / "features" / f"{f.stem}.npz"
        if not dest.exists():
            np.savez(dest, **page_features(model, f.stem, json.loads(f.read_text())["instances"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
