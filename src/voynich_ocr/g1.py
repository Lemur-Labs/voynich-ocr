import hashlib
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np

from voynich_ocr import disagreement as d
from voynich_ocr import ivtff, scoring
from voynich_ocr.align import majority
from voynich_ocr.snapshot import RAW, ROOT
from voynich_ocr.splits import NATIVE, TEST_SOURCES
from voynich_ocr.sta import Glyph

IVTT_SOURCE = RAW / "ivtt" / "ivtt.c"
IVTT = ROOT / "build" / "ivtt"
OUT = ROOT / "results" / "g1"
PERTURBATION_SEED = 20261031
COVERAGE_SEED = 20261031
COVERAGE_DRAWS = 200
COVERAGE_PAGES = 40
SPOT_CHECK_SEED = 20261031
SPOT_CHECK_LOCI = 20


def _hashes(directory: Path) -> dict[str, str]:
    return {
        str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(directory.rglob("*"))
        if p.is_file()
    }


def determinism() -> dict:
    runs = []
    for _ in range(2):
        subprocess.run(["make", "map"], cwd=ROOT, check=True, capture_output=True)
        runs.append(_hashes(ROOT / "build" / "map"))
    return {"identical": runs[0] == runs[1], "files": runs[0]}


def parser_against_ivtt() -> dict:
    IVTT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["cc", "-O1", "-w", "-o", str(IVTT), str(IVTT_SOURCE)], check=True)
    files = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, rel in NATIVE.items():
            out = Path(tmp) / name
            # ivtt exits 3 on success (ivtt.c `return 3`) and reads stdin when given no input.
            r = subprocess.run(
                [str(IVTT), "-x2", str(RAW / rel), str(out)],
                check=False,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
            )
            if r.returncode != 3 or not out.exists():
                raise RuntimeError(f"ivtt failed on {rel}: {r.returncode} {r.stderr[-300:]}")
            theirs = out.read_text().splitlines()
            parsed = ivtff.parse((RAW / rel).read_text())
            mine = [ivtff.plain_text(lo.text) for lo in parsed.loci if lo.exists]
            files[name] = {
                "loci": len(parsed.loci),
                "not_in_manuscript": [lo.id for lo in parsed.loci if not lo.exists],
                "ivtt_lines": len(theirs),
                "identical": mine == theirs,
            }
    return {"identical": all(f["identical"] for f in files.values()), "files": files}


def fixture() -> dict:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(ROOT / "tests" / "test_align.py")],
        check=False,
        capture_output=True,
        text=True,
    )
    return {"passed": r.returncode == 0, "pytest": r.stdout.strip().splitlines()[-1]}


def _edit(glyphs: list[Glyph], rng: np.random.Generator, codes: list[str], aaa: dict[str, str]):
    """One copy of the line with substitutions, deletions and insertions at least three glyphs apart, away from
    identical runs (where a position is ambiguous by construction) and joining none, and each using only `codes` so that
    no source is masked out of the edited column. Returns the copy and the expected (ZL, copy) readings of
    the disputed columns."""
    tokens = [d.token(g.code, aaa) for g in glyphs]
    out = list(glyphs)
    expected: Counter = Counter()
    for i in range(len(glyphs) - 2, 0, -4):
        left, right = tokens[i - 1], tokens[i + 1]
        if d.UNKNOWN in (left, tokens[i], right) or tokens[i] in (left, right) or glyphs[i].code not in codes:
            continue
        if rng.random() < 0.5:
            continue
        kind = rng.integers(3)
        choices = [c for c in codes if aaa[c] not in (left, right, tokens[i])]
        new = Glyph(choices[rng.integers(len(choices))], False, "")
        if kind == 1 and left != right:
            del out[i]
            expected[((tokens[i],), ())] += 1
        elif kind == 0:
            out[i] = new
            expected[((tokens[i],), (aaa[new.code],))] += 1
        else:
            out.insert(i + 1, new)
            expected[((), (aaa[new.code],))] += 1
    return out, expected


def _columns(locus: d.Locus, texts: dict[str, list[Glyph]], inputs: d.Inputs) -> list[d.Column]:
    sources = {s: d.Source({locus.id: g}, inputs.sources[s].codes) for s, g in texts.items()}
    return d.locus_columns(locus, d.Inputs(sources, [locus], inputs.aaa), d.ORDER)[0]


def _disputed(cols: list[d.Column], target: str) -> Counter:
    return Counter(
        (c.readings["ZL"], c.readings[target]) for c in cols if c.cls in ("disagree", "granularity")
    )


def perturbation() -> dict:
    """Five copies of each ZL line, each source keeping its own expressible codes, must agree everywhere with
    no source masked;
    perturbing one copy must yield exactly the edited readings as disputed columns and nothing else."""
    inputs = d.load()
    zl = inputs.sources["ZL"].loci
    shared = sorted(frozenset.intersection(*(inputs.sources[s].codes for s in d.ORDER)) - {"Z1"})
    rng = np.random.default_rng(PERTURBATION_SEED)
    clean_disputed, clean_masked, injected, recovered, extra = 0, 0, 0, 0, 0
    for locus in inputs.loci:
        if locus.id not in zl or not zl[locus.id]:
            continue
        line = zl[locus.id]
        copies = {s: list(line) for s in d.ORDER}
        target = d.ORDER[1 + rng.integers(len(d.ORDER) - 1)]
        clean = _columns(locus, copies, inputs)
        clean_disputed += sum(_disputed(clean, target).values())
        clean_masked += sum(len(c.contributing) < c.tier for c in clean)
        copies[target], expected = _edit(line, rng, shared, inputs.aaa)
        found = _disputed(_columns(locus, copies, inputs), target)
        matched = sum((expected & found).values())
        injected += sum(expected.values())
        recovered += matched
        extra += sum(found.values()) - matched
    return {
        "seed": PERTURBATION_SEED,
        "shared_codes": len(shared),
        "disputed_on_unperturbed": clean_disputed,
        "masked_on_unperturbed": clean_masked,
        "injected": injected,
        "recovered": recovered,
        "spurious": extra,
        "passed": clean_disputed == 0 and clean_masked == 0 and recovered == injected and extra == 0,
    }


def coverage() -> dict:
    """H3's coverage figures on non-test pages, for fixing scoring.MIN_GROUP_COVERAGE at G1. The token is the
    column's majority reading, standing in for the recognizer's glyph; one entry per glyph of that reading."""
    inputs = d.load()
    splits = json.loads(d.SPLITS.read_text())
    test = set(splits["test"])
    columns, _ = d.build(inputs, d.MAPS["full"])
    eligible = sorted(
        {lo.page for lo in inputs.loci if all(lo.id in inputs.sources[s].loci for s in TEST_SOURCES)} - test
    )
    tokens, disagree, pages = [], [], []
    for c in columns:
        if c.page in test or not c.gated:
            continue
        reading = majority([c.readings[s] for s in c.contributing])
        for t in reading:
            tokens.append(t)
            disagree.append(c.cls == "disagree")
            pages.append(c.page)
    tokens, disagree, pages = np.array(tokens), np.array(disagree), np.array(pages)

    def figures(mask):
        return (
            scoring.within_type_coverage(disagree[mask], tokens[mask]),
            scoring.within_page_coverage(disagree[mask], pages[mask]),
        )

    rng = np.random.default_rng(COVERAGE_SEED)
    draws = []
    for _ in range(COVERAGE_DRAWS):
        chosen = rng.choice(eligible, size=COVERAGE_PAGES, replace=False)
        draws.append(figures(np.isin(pages, chosen)))
    draws = np.array(draws)
    void_share = float((draws.min(axis=1) < scoring.MIN_GROUP_COVERAGE).mean())
    all_type, all_page = figures(np.ones(len(pages), dtype=bool))
    return {
        "seed": COVERAGE_SEED,
        "glyphs": len(tokens),
        "pages": len(set(pages.tolist())),
        "within_type_all_nontest": round(all_type, 4),
        "within_page_all_nontest": round(all_page, 4),
        f"{COVERAGE_PAGES}_page_draws_from_{len(eligible)}_eligible": {
            "within_type_p5_p50_p95": [round(float(x), 4) for x in np.percentile(draws[:, 0], [5, 50, 95])],
            "within_page_p5_p50_p95": [round(float(x), 4) for x in np.percentile(draws[:, 1], [5, 50, 95])],
            f"void_share_at_{scoring.MIN_GROUP_COVERAGE}": round(void_share, 4),
        },
    }


def spot_check_sample() -> list[dict]:
    """One locus with a gated disagreement from each of 20 non-test pages, for checking against the images."""
    inputs = d.load()
    test = d.test_pages()
    disputed: dict[str, dict[str, list[d.Column]]] = {}
    for locus in inputs.loci:
        if locus.page in test:
            continue
        cols, _ = d.locus_columns(locus, inputs, d.MAPS["full"])
        hits = [c for c in cols if c.gated and c.cls == "disagree"]
        if hits:
            disputed.setdefault(locus.page, {})[locus.id] = hits
    rng = np.random.default_rng(SPOT_CHECK_SEED)
    pages = sorted(rng.choice(sorted(disputed), size=SPOT_CHECK_LOCI, replace=False).tolist())
    sample = []
    for page in pages:
        loci = sorted(disputed[page])
        locus = loci[rng.integers(len(loci))]
        sample.append(
            {
                "locus": locus,
                "native": {
                    s: ivtff.plain_text(lo.text)
                    for s, rel in NATIVE.items()
                    for lo in ivtff.parse((RAW / rel).read_text()).loci
                    if lo.id == locus and lo.exists
                },
                "disputed_columns": [
                    {"column": c.index, "readings": {s: " ".join(r) or "-" for s, r in c.readings.items()}}
                    for c in disputed[page][locus]
                ],
            }
        )
    return sample


def decide_map(checks: dict) -> str:
    """G1 per docs/prereg.md H1: pass when all four checks hold. Kill is reserved for unparseable data, which
    raises before this point."""
    ok = (
        checks["determinism"]["identical"]
        and checks["parser"]["identical"]
        and checks["fixture"]["passed"]
        and checks["perturbation"]["passed"]
    )
    return "pass" if ok else "not ready"


def main() -> int:
    checks = {
        "determinism": determinism(),
        "parser": parser_against_ivtt(),
        "fixture": fixture(),
        "perturbation": perturbation(),
    }
    checks["outcome"] = decide_map(checks)
    checks["coverage"] = coverage()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "checks.json").write_text(json.dumps(checks, indent=1) + "\n")
    print(checks["outcome"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
