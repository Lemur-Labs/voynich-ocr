import argparse
import hashlib
import sys
import tomllib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "snapshot" / "sources.toml"
MANIFEST = ROOT / "snapshot" / "manifest.sha256"
RAW = ROOT / "data" / "raw"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_sources(sources: Path = SOURCES) -> list[dict]:
    return tomllib.loads(sources.read_text())["source"]


def read_manifest(manifest: Path = MANIFEST) -> dict[str, str]:
    pins = {}
    for line in manifest.read_text().splitlines():
        digest, path = line.split("  ", 1)
        pins[path] = digest
    return pins


def write_manifest(pins: dict[str, str], manifest: Path = MANIFEST) -> None:
    manifest.write_text("".join(f"{pins[p]}  {p}\n" for p in sorted(pins)))


def fetch(sources: list[dict], raw: Path = RAW) -> None:
    for s in sources:
        dest = raw / s["path"]
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(s["url"], headers={"User-Agent": "voynich-ocr snapshot"})
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(body)
        tmp.rename(dest)


def mismatches(pins: dict[str, str], raw: Path = RAW) -> list[str]:
    bad = []
    for path, digest in sorted(pins.items()):
        f = raw / path
        if not f.exists():
            bad.append(f"missing  {path}")
        elif sha256(f) != digest:
            bad.append(f"changed  {path}")
    return bad


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="snapshot")
    p.add_argument("command", choices=["fetch", "pin", "verify"])
    args = p.parse_args(argv)
    sources = load_sources()
    if args.command == "fetch":
        fetch(sources)
        return 0
    if args.command == "pin":
        write_manifest({s["path"]: sha256(RAW / s["path"]) for s in sources})
        return 0
    bad = mismatches(read_manifest())
    for line in bad:
        print(line, file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
