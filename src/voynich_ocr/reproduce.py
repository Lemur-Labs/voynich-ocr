"""Byte-diff the regenerated map against the committed record and the map-v0 release.

`make reproduce` runs this after `make g1` has regenerated build/map and results/g1/checks.json.
Every published artifact must match the committed summary (results/map-v0/summary.json) and the
digests the map-v0 release's SHA256SUMS pins; the per-column TSVs are compared byte-for-byte with
the uncompressed release assets. Exits non-zero on the first mismatch.
"""

import gzip
import hashlib
import json
import sys
import urllib.request
from collections.abc import Iterator
from typing import Any

from voynich_ocr.snapshot import ROOT

RELEASE_TAG = "map-v0"
RELEASE_URL = f"https://github.com/Lemur-Labs/voynich-ocr/releases/download/{RELEASE_TAG}"
BUILD = ROOT / "build" / "map"
COMMITTED = ROOT / "results" / "map-v0"
G1_CHECKS = ROOT / "results" / "g1" / "checks.json"
G1_EXPECTED = ROOT / "build" / "reproduce" / "g1-checks-expected.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_release(name: str) -> bytes:
    req = urllib.request.Request(f"{RELEASE_URL}/{name}", headers={"User-Agent": "voynich-ocr reproduce"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def read_sums(sums: str) -> dict[str, str]:
    pins = {}
    for line in sums.splitlines():
        digest, name = line.split("  ", 1)
        pins[name] = digest
    return pins


def check_summary(pins: dict[str, str]) -> None:
    built = (BUILD / "summary.json").read_bytes()
    committed = (COMMITTED / "summary.json").read_bytes()
    if built != committed:
        sys.exit("mismatch: build/map/summary.json differs from results/map-v0/summary.json")
    pinned = pins["summary.json"]
    if sha256(built) != pinned:
        sys.exit(f"mismatch: build/map/summary.json digest differs from the {RELEASE_TAG} SHA256SUMS pin {pinned}")
    print(f"ok  summary.json  {pinned}")


def check_published_tsvs(pins: dict[str, str]) -> None:
    for name, digest in sorted(pins.items()):
        if not name.endswith(".tsv.gz"):
            continue
        release_asset = gzip.decompress(fetch_release(name))
        built_name = name.removesuffix(".gz")
        built = (BUILD / "published" / built_name).read_bytes()
        if built != release_asset:
            sys.exit(f"mismatch: build/map/published/{built_name} differs from the {RELEASE_TAG} release asset {name}")
        print(f"ok  published/{built_name}  {digest}")


def flatten(value: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    for key, child in value.items():
        path = f"{prefix}{key}"
        if isinstance(child, dict):
            yield from flatten(child, f"{path}.")
        else:
            yield path, child


def check_g1_checks() -> None:
    committed = dict(flatten(json.loads(G1_EXPECTED.read_text())))
    current = dict(flatten(json.loads(G1_CHECKS.read_text())))
    shared = committed.keys() & current.keys()
    changed = [k for k in sorted(shared) if committed[k] != current[k]]
    if changed:
        sys.exit(f"mismatch: results/g1/checks.json changed for: {', '.join(changed)}")
    # The committed checks.json is the G1-era record. Later prereg amendments may add digests
    # for the published-test TSVs and rename the void-share key to the current coverage
    # minimum (A5 moved it 0.72 -> 0.56). Any other difference is a mismatch.
    added = current.keys() - committed.keys()
    unexplained = [
        k
        for k in sorted(added)
        if not k.startswith("determinism.files.published-test/") and ".void_share_at_" not in k
    ]
    if unexplained:
        sys.exit(f"mismatch: results/g1/checks.json has unexplained new keys: {', '.join(unexplained)}")
    print(f"ok  results/g1/checks.json  {len(shared)} shared keys match, {len(added)} amendment keys added")


def main() -> int:
    pins = read_sums(fetch_release("SHA256SUMS").decode())
    check_summary(pins)
    check_published_tsvs(pins)
    check_g1_checks()
    return 0


if __name__ == "__main__":
    sys.exit(main())
