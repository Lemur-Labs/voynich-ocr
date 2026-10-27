import json
import re
import sys
from collections import defaultdict

import numpy as np

from voynich_ocr.snapshot import RAW, ROOT, read_manifest

SPLIT_SEED = 20261027
TEST_SHARE = 0.2
VALIDATION_PAGES = 12
NATIVE = {
    "ZL": "transliterations/native/ZL3b-n.txt",
    "IT": "transliterations/native/IT2a-n.txt",
    "CD": "transliterations/native/CD2a-n.txt",
    "GC": "transliterations/native/GC2a-n.txt",
    "FG": "transliterations/native/FG2a-n.txt",
}
# Test pages need at least four independent readings so that leave-ZL-out keeps three; CD covers too few
# sections (herbal and balneological only) to be required.
TEST_SOURCES = ("ZL", "IT", "GC", "FG")
OUT = ROOT / "docs" / "prereg" / "splits.json"

_PAGE = re.compile(r"^<(f[0-9a-z]+)>(.*)$")
_VAR = re.compile(r"\$([A-Z])=(\S)")


def page_headers(text: str) -> dict[str, dict[str, str]]:
    pages = {}
    for line in text.splitlines():
        m = _PAGE.match(line)
        if m:
            pages[m.group(1)] = dict(_VAR.findall(m.group(2)))
    return pages


def make_splits(native: dict[str, str]) -> dict:
    headers = {k: page_headers(v) for k, v in native.items()}
    zl = headers["ZL"]
    eligible = sorted(set.intersection(*(set(headers[k]) for k in TEST_SOURCES)))
    strata = defaultdict(list)
    for p in eligible:
        strata[(zl[p].get("I", "?"), zl[p].get("L", "?"))].append(p)
    rng = np.random.default_rng(SPLIT_SEED)
    test = []
    for key in sorted(strata):
        members = sorted(strata[key])
        k = round(len(members) * TEST_SHARE)
        test += sorted(rng.choice(members, size=k, replace=False).tolist()) if k else []
    rest = sorted(set(zl) - set(test))
    validation = sorted(rng.choice(rest, size=VALIDATION_PAGES, replace=False).tolist())
    return {
        "seed": SPLIT_SEED,
        "eligible_pages": len(eligible),
        "five_way_pages": len(set.intersection(*(set(h) for h in headers.values()))),
        "test": sorted(test),
        "validation": validation,
        "strata": {f"{i}/{lang}": len(v) for (i, lang), v in sorted(strata.items())},
    }


def main() -> int:
    pins = read_manifest()
    native = {k: (RAW / p).read_text() for k, p in NATIVE.items()}
    splits = make_splits(native)
    splits["inputs"] = {NATIVE[k]: pins[NATIVE[k]] for k in NATIVE}
    OUT.write_text(json.dumps(splits, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
