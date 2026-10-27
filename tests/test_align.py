import json
from pathlib import Path

import pytest

from voynich_ocr.align import align, majority

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "alignment.json").read_text())


def _rendered(sources: list[str | None]) -> list[str | None]:
    present = [list(s) for s in sources if s is not None]
    columns = align(present, FIXTURE["unknown"])
    rows = iter("".join("-" if c[k] is None else present[k][c[k]] for c in columns) for k in range(len(present)))
    return [None if s is None else next(rows) for s in sources]


@pytest.mark.parametrize("locus", FIXTURE["loci"], ids=[locus["name"] for locus in FIXTURE["loci"]])
def test_frozen_fixture(locus):
    assert _rendered(locus["sources"]) == locus["columns"]


def test_fixture_has_ten_loci():
    assert len(FIXTURE["loci"]) == 10


def test_majority_counts_gaps_and_breaks_ties_by_source_order():
    assert majority(["x", None, None]) is None
    assert majority([None, "x"]) is None
    assert majority(["y", "x", "x", "y"]) == "y"
