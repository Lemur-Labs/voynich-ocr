import hashlib
import json
from pathlib import Path

from voynich_ocr.snapshot import ROOT

MODEL = ROOT / "build" / "model" / "20261027" / "best_0.9452.safetensors"
STATIC = ["docs/prereg/splits.json", "snapshot/manifest.sha256", "uv.lock"]
OUTPUTS = ["build/seg", "build/instances", "build/clusters/features", "build/g3"]
DECISIONS = ROOT / "docs" / "decisions.yaml"


def frozen_files(root: Path = ROOT) -> list[str]:
    """Code, split, snapshot manifest, locked dependencies, the line dataset, and the non-test pages' segmentation,
    instances and features, and the G3 temperature; test-page outputs are made after the freeze, so they stay out."""
    test = set(json.loads((root / "docs" / "prereg" / "splits.json").read_text())["test"])
    files = [p for p in (root / "src" / "voynich_ocr").glob("*.py")]
    files += [p for p in (root / "build" / "lines").rglob("*") if p.is_file()]
    files += [p for d in OUTPUTS for p in (root / d).glob("*") if p.is_file() and p.stem not in test]
    return sorted([str(p.relative_to(root)) for p in files] + STATIC)


def config_hash(model: Path, root: Path = ROOT) -> str:
    h = hashlib.sha256()
    for rel in frozen_files(root):
        h.update(rel.encode() + b"\0" + (root / rel).read_bytes())
    h.update(hashlib.sha256(model.read_bytes()).digest())
    return h.hexdigest()


def require(model: Path = MODEL, decisions: Path = DECISIONS, root: Path = ROOT) -> None:
    digest = config_hash(model, root)
    if digest not in decisions.read_text():
        raise SystemExit(f"config hash {digest} is not recorded in {decisions.name}; test pages stay unread")
