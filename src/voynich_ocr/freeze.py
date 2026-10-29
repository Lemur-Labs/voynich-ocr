import hashlib
from pathlib import Path

from voynich_ocr.snapshot import ROOT

MODEL = ROOT / "build" / "model" / "20261027" / "best_0.9452.safetensors"
FROZEN = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "src" / "voynich_ocr").glob("*.py")) + [
    "docs/prereg/splits.json", "snapshot/manifest.sha256", "uv.lock",
    "build/lines/codec.json", "build/lines/train.txt", "build/lines/eval.txt",
]  # fmt: skip
DECISIONS = ROOT / "docs" / "decisions.yaml"


def config_hash(model: Path) -> str:
    """Every input that can change an H2 result: code, split, snapshot manifest, locked dependencies, line labels and
    the recognizer."""
    h = hashlib.sha256()
    for rel in FROZEN:
        h.update(rel.encode() + b"\0" + (ROOT / rel).read_bytes())
    h.update(hashlib.sha256(model.read_bytes()).digest())
    return h.hexdigest()


def require(model: Path = MODEL, decisions: Path = DECISIONS) -> None:
    digest = config_hash(model)
    if digest not in decisions.read_text():
        raise SystemExit(f"config hash {digest} is not recorded in {decisions.name}; test pages stay unread")
