import hashlib
import re

import yaml

from voynich_ocr.snapshot import ROOT

DOCS = ROOT / "docs"


def test_decisions_parse_into_rows_with_unique_ids():
    rows = yaml.safe_load((DOCS / "decisions.yaml").read_text())
    assert len({r["id"] for r in rows}) == len(rows)


def test_prereg_matches_the_latest_pinned_sha():
    rows = yaml.safe_load((DOCS / "decisions.yaml").read_text())
    pins = [m[1] for r in rows if (m := re.search(r"docs/prereg\.md .*has sha256 ([0-9a-f]{64})", r["decision"]))]
    assert hashlib.sha256((DOCS / "prereg.md").read_bytes()).hexdigest() == pins[-1]
