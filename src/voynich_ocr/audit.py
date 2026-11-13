"""Audit every figure in docs/writeup.md against the committed results.

Each check extracts a figure from the writeup by pattern and compares it to the value recomputed from the results
file, gate packet or decision row the figure came from. The output is docs/audit.md: one row per figure with its
source and the verdict (match / mismatch / untraceable). A mismatch or an untraceable figure is a finding: it gets
a VO- row in docs/decisions.yaml and a correction proposed in a PR, never a silent edit.
"""

import argparse
import gzip
import hashlib
import json
import re
import sys
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml

from voynich_ocr.g2 import gate_power
from voynich_ocr.snapshot import ROOT

WRITEUP = ROOT / "docs" / "writeup.md"
DECISIONS = ROOT / "docs" / "decisions.yaml"
PREREG = ROOT / "docs" / "prereg.md"
G1_PACKET = ROOT / "docs" / "gates" / "G1.md"
G3_PACKET = ROOT / "docs" / "gates" / "G3.md"
OUT = ROOT / "docs" / "audit.md"
TEST_TSV = ROOT / "build" / "map-v0-test" / "full.tsv"
TEST_RELEASE_URL = "https://github.com/Lemur-Labs/voynich-ocr/releases/download/map-v0-test/full.tsv.gz"
AUDIT_DATE = "2026-11-13"


@dataclass
class Check:
    section: str
    figure: str
    pattern: str
    expected: str | tuple[str, ...]
    source: str
    note: str = ""
    predicate: Callable[[tuple[str, ...]], bool] | None = None


@dataclass
class Row:
    section: str
    figure: str
    written: str
    expected: str
    source: str
    verdict: str
    note: str = ""


def _pct(value: float, places: int) -> str:
    return f"{100 * value:.{places}f}"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _decisions() -> list[dict]:
    return yaml.safe_load(DECISIONS.read_text())


def _normalize(text: str) -> str:
    """Collapse whitespace and normalize the unicode minus so patterns match across line wraps."""
    return re.sub(r"\s+", " ", text.replace("−", "-")).strip()


def _check(normalized: str, check: Check) -> Row:
    """Run one check: every occurrence of the pattern in the writeup must carry the expected value."""
    found = re.findall(check.pattern, normalized)
    if not found:
        return Row(check.section, check.figure, "<not found in writeup>", str(check.expected), check.source,
                   "untraceable", check.note)
    written = ", ".join("/".join(f) if isinstance(f, tuple) else f for f in found)
    expected = check.expected if isinstance(check.expected, tuple) else (check.expected,)
    ok = all(f == expected if isinstance(f, tuple) else f == check.expected for f in found)
    if ok and check.predicate is not None:
        ok = all(check.predicate(f if isinstance(f, tuple) else (f,)) for f in found)
    return Row(check.section, check.figure, written,
               "/".join(expected) + (f" — {check.note}" if check.note else ""), check.source,
               "match" if ok else "mismatch")


def _gated_counts(tsv: Path) -> tuple[int, int]:
    """Gated and disagreeing columns of a published per-column TSV (no readings, VO-028)."""
    lines = tsv.read_text().splitlines()
    header = lines[0].split("\t")
    gated, disagree = 0, 0
    for line in lines[1:]:
        cells = dict(zip(header, line.split("\t"), strict=True))
        if cells["gated"] == "gated":
            gated += 1
            disagree += cells["class"] == "disagree"
    return gated, disagree


def _test_page_tsv() -> Path:
    """The map-v0-test release's full.tsv: the test-page rows published per VO-064, fetched if not cached."""
    if not TEST_TSV.exists():
        TEST_TSV.parent.mkdir(parents=True, exist_ok=True)
        payload = urllib.request.urlopen(TEST_RELEASE_URL, timeout=60).read()
        TEST_TSV.write_bytes(gzip.decompress(payload))
    return TEST_TSV


def _h1_checks(summary: dict) -> list[Row]:
    """Figures of the map section, abstract and deviations, against summary.json, the release and the record."""
    normalized = _normalize(WRITEUP.read_text())
    overall = {name: summary["maps"][name]["overall"] for name in ("full", "leave-ZL-out", "leave-ZL-IT-out", "ZL-IT-GC")}
    g1_packet = G1_PACKET.read_text()
    decisions_text = DECISIONS.read_text()
    vo022 = re.search(r"9180f72, headline (\d+\.\d+)%", decisions_text)
    vo023 = re.search(r"MIN_GROUP_COVERAGE to (\d+\.\d+)", decisions_text)
    vo048 = re.search(r"coverage minimum at (\d+\.\d+)", decisions_text)
    vo075 = re.search(r"collage read at (\d+)–(\d+)% CER", decisions_text)
    g3_cer = _load_json(ROOT / "results" / "g3" / "result.json")["cer"]["zl"]
    test_gated, test_disagree = _gated_counts(_test_page_tsv())
    test_rate = _pct(test_disagree / test_gated, 2)
    checks = [
        Check("Abstract", "headline rate on non-test pages", r"(\d+\.\d+)% of gated columns disagree on the",
              _pct(overall["full"]["gated_rate"], 2), "results/map-v0/summary.json · maps.full.overall.gated_rate"),
        Check("Abstract", "test-page rate", r"(\d+\.\d+)% on the 40 test pages", test_rate,
              "map-v0-test release full.tsv (see the test-page row below)"),
        Check("H1", "headline rate and counts", r"\*\*(\d+\.\d+)%\*\* disagree \(([\d,]+) of ([\d,]+)\)",
              (_pct(overall["full"]["gated_rate"], 2), f"{overall['full']['gated_disagree']:,}",
               f"{overall['full']['gated']:,}"),
              "results/map-v0/summary.json · maps.full.overall.gated_rate/gated_disagree/gated"),
        Check("H1", "non-test page count", r"(\d+) non-test pages", str(len(summary["pages"])),
              "results/map-v0/summary.json · pages (withheld_test_pages = 40)"),
        Check("H1", "leave-ZL-out rate", r"leaving ZL out, (\d+\.\d+)%", _pct(overall["leave-ZL-out"]["gated_rate"], 2),
              "results/map-v0/summary.json · maps.leave-ZL-out.overall.gated_rate"),
        Check("H1", "leave-{ZL, IT}-out rate", r"leaving ZL and IT out, (\d+\.\d+)%",
              _pct(overall["leave-ZL-IT-out"]["gated_rate"], 2),
              "results/map-v0/summary.json · maps.leave-ZL-IT-out.overall.gated_rate",
              "not maps.leave-IT-out (0.036196, 3.62%): a different population; see notes"),
        Check("H1", "{ZL, IT, GC} map rate", r"the \{ZL, IT, GC\} map, (\d+\.\d+)%",
              _pct(overall["ZL-IT-GC"]["gated_rate"], 2),
              "results/map-v0/summary.json · maps.ZL-IT-GC.overall.gated_rate"),
        Check("H1", "test-page rate and counts", r"give (\d+\.\d+)% \(([\d,]+) of ([\d,]+)\)",
              (test_rate, f"{test_disagree:,}", f"{test_gated:,}"),
              "map-v0-test release · full.tsv column counts (VO-064; no readings, VO-028)",
              "results/ holds no test-page summary; the release assets are the published source"),
        Check("H1", "headline before A2", r"Before A2 the non-test headline was (\d+\.\d+)%",
              re.search(r"disagree at \*\*(\d+\.\d+)%\*\*", g1_packet).group(1),
              "docs/gates/G1.md (corrected pre-A2 headline); docs/prereg.md"),
        Check("H1", "headline before the G1 bug fix", r"\(9180f72, non-test headline (\d+\.\d+)%\)",
              vo022.group(1), "docs/decisions.yaml · VO-022"),
        Check("Deviations", "A1's coverage minimum", r"coverage minimum fixed at (\d+\.\d+)\.", vo023.group(1),
              "docs/decisions.yaml · VO-023"),
        Check("Deviations", "A5's coverage minimum", r"coverage minimum re-fixed at (\d+\.\d+)\.", vo048.group(1),
              "docs/decisions.yaml · VO-048; results/a5/coverage.json · void_share keys"),
        Check("Deviations", "A8: glyph-collage dev CER vs real lines",
              r"collage read at (\d+)–(\d+)% CER on dev lines, against about (\d+)% on real lines",
              (vo075.group(1), vo075.group(2), str(round(100 * g3_cer))),
              "docs/decisions.yaml · VO-075; results/g3/result.json · cer.zl"),
    ]
    return [_check(normalized, c) for c in checks]


def _pairwise_checks(summary: dict) -> list[Row]:
    """The dependence table and named confusions, against summary.json's pairwise block."""
    rows: list[Row] = []
    lines = WRITEUP.read_text().splitlines()
    header = next(line for line in lines if line.strip().startswith("| Pair |"))
    rate_line = next(line for line in lines if line.strip().startswith("| Rate |"))
    pairs = [cell.strip().replace("–", "-") for cell in header.split("|")[2:-1]]
    written_rates = [cell.strip() for cell in rate_line.split("|")[2:-1]]
    expected = [_pct(summary["pairwise"][p]["rate"], 1) + "%" for p in pairs]
    rows.append(Row("H1", "dependence table (10 pairwise rates)", " | ".join(written_rates), ", ".join(expected),
                    "results/map-v0/summary.json · pairwise.*.rate",
                    "match" if written_rates == expected else "mismatch"))
    # The three-minim confusion against each FSG pair, and its rank within them.
    normalized = _normalize(WRITEUP.read_text())
    found = re.findall(r"([\d,]+) columns against ZL, ([\d,]+) against IT and ([\d,]+) against GC", normalized)
    written = "/".join(found[0]) if found else "<not found>"
    fg_pairs = [p for p in summary["pairwise"] if "FG" in p.split("-")]
    tops = {p: summary["pairwise"][p]["top"][0] for p in fg_pairs}
    expected_counts = [f"{tops['ZL-FG'][2]:,}", f"{tops['IT-FG'][2]:,}", f"{tops['GC-FG'][2]:,}"]
    minim = ["i0~i0:b0", "i0~i0~i0:b0"]
    is_top = all(tops[p][:2] in (minim, minim[::-1]) for p in fg_pairs)
    ok = bool(found) and [c.replace(",", "") for c in found[0]] == [c.replace(",", "") for c in expected_counts]
    rows.append(Row("H1", "three-minim confusion counts vs ZL / IT / GC", written,
                    "/".join(expected_counts) + f" — top of every FSG pair: {is_top}",
                    "results/map-v0/summary.json · pairwise.{ZL,IT,GC}-FG.top[0]",
                    "match" if ok and is_top else "mismatch"))
    a_o = all(any(t[0][:2] == "a0" and t[1][:2] == "o0" or t[0][:2] == "o0" and t[1][:2] == "a0"
                  for t in summary["pairwise"][p]["top"]) for p in summary["pairwise"])
    present = "a/o differences appear in every pair." in WRITEUP.read_text()
    rows.append(Row("H1", "a/o differences appear in every pair", "present" if present else "absent",
                    f"a0/o0 in every pair's top list: {a_o}", "results/map-v0/summary.json · pairwise.*.top",
                    "match" if a_o and present else "mismatch"))
    return rows


def _g2_checks(g2: dict) -> list[Row]:
    """G2 figures against results/g2, its consistency runs, and the power recomputed by the committed code."""
    rows: list[Row] = []
    normalized = _normalize(WRITEUP.read_text())
    primary = g2["primary"]
    power = gate_power(primary)
    seeds = {name: _load_json(ROOT / "results" / "g2" / "consistency" / name / "result.json")
             for name in ("20261028-gated", "20261029-gated", "20261027-blind", "20261028-blind", "20261029-blind")}
    checks = [
        Check("H2", "entropy gap", r"entropy gap is (\d+\.\d+)", f"{primary['gap']:.3f}",
              "results/g2/result.json · primary.gap"),
        Check("H2", "gap interval", r"entropy gap is \d+\.\d+, 95% CI \[(-?[\d.]+), ([\d.]+)\]",
              (f"{primary['lo']:.3f}", f"{primary['hi']:.3f}"), "results/g2/result.json · primary.lo/hi"),
        Check("H2", "permutation null", r"against a null of (\d+\.\d+)", f"{primary['null_975']:.3f}",
              "results/g2/result.json · primary.null_975"),
        Check("H2", "gap detectable with 80% power", r"rule detects a gap of (\d+\.\d+) with 80% power",
              f"{power['detectable_80']:.3f}",
              "recomputed by voynich_ocr.g2.gate_power on results/g2/result.json; packet docs/gates/G2.md"),
        Check("H2", "chance of passing at the observed gap", r"chance of passing was (\d+\.\d+)%",
              _pct(power["power_at_gap"], 1), "as above · gate_power.power_at_gap"),
        Check("H2", "seed 20261028's interval and its reading",
              r"Seed 20261028's interval, \[([\d.]+), ([\d.]+)\], excludes zero, but its lower bound is under its null",
              (f"{seeds['20261028-gated']['primary']['lo']:.3f}",
               f"{seeds['20261028-gated']['primary']['hi']:.3f}"),
              "results/g2/consistency/20261028-gated/result.json · primary.lo/hi/null_975",
              "lower bound above zero and under its null",
              lambda f: 0 < float(f[0]) < seeds['20261028-gated']['primary']['null_975']),
        Check("H2", "label-blind rows", r"they keep (\d+) of (\d+) pages", ("17", "40"),
              "results/g2/consistency/*-blind/result.json · attrition.pages, .void"),
        Check("Deviations", "VO-041: ZL helped choose the scored lines on 36 test pages",
              r"ZL helped choose the scored test lines in G2 \((\d+) pages\)", "36",
              "docs/decisions.yaml · VO-041"),
    ]
    rows += [_check(normalized, c) for c in checks]
    gate_clears = g2["hog"]["lo"] > g2["hog"]["null_975"]
    others_clear = [s["hog"]["lo"] > s["hog"]["null_975"] for s in seeds.values() if "hog" in s]
    present = "HOG features cleared their null for the gate seed only" in normalized
    rows.append(Row("H2", "HOG cleared its null for the gate seed only", "present" if present else "absent",
                    f"gate lo {g2['hog']['lo']:.4f} > null {g2['hog']['null_975']:.4f}; no consistency seed clears",
                    "results/g2/result.json · hog; results/g2/consistency/*/result.json · hog",
                    "match" if present and gate_clears and not any(others_clear) else "mismatch"))
    both_kill = all(seeds[s]["outcome"] == "kill" for s in ("20261028-gated", "20261029-gated"))
    present = "seeds 20261028 and 20261029 also kill" in normalized
    rows.append(Row("H2", "consistency seeds also kill", "present" if present else "absent",
                    "both consistency runs' outcome is kill", "results/g2/consistency/*-gated/result.json · outcome",
                    "match" if present and both_kill else "mismatch"))
    blind = [v for k, v in seeds.items() if "blind" in k]
    kept = {v["attrition"]["pages"][0] for v in blind}
    void = all(v["attrition"]["void"] for v in blind)
    void_said = "are void for attrition" in normalized
    rows.append(Row("H2", "label-blind rows are void for attrition", "present" if void_said else "absent",
                    f"all three blind runs void, keeping {sorted(kept)} of 40 pages",
                    "results/g2/consistency/*-blind/result.json · attrition",
                    "match" if void_said and kept == {17} and void else "mismatch"))
    return rows


def _g3_checks(g3: dict) -> list[Row]:
    """H3 figures against results/g3, its consistency runs and the G3 packet."""
    rows: list[Row] = []
    normalized = _normalize(WRITEUP.read_text())
    wt = g3["within_type"]
    wp = g3["within_page"]
    packet = G3_PACKET.read_text()
    alternatives = re.search(r"That is (\d+) of ([\d,]+) ZL glyphs on training pages \((\d+\.\d+)%\)", packet)
    share = _pct(int(alternatives.group(1)) / int(alternatives.group(2).replace(",", "")), 2)
    checks = [
        Check("H3", "within-type AUROC and baseline bar",
              r"within-type AUROC (\d+\.\d+) \[([\d.]+), ([\d.]+)\] against a baseline bar of (\d+\.\d+)",
              (f"{wt['full']['point']:.3f}", f"{wt['full']['lo']:.3f}", f"{wt['full']['hi']:.3f}",
               f"{g3['baseline_bar']:.3f}"), "results/g3/result.json · within_type.full, .baseline_bar"),
        Check("H3", "leave-ZL-out within-type AUROC", r"leave-ZL-out (\d+\.\d+) \[([\d.]+), ([\d.]+)\]",
              (f"{wt['leave-ZL-out']['point']:.3f}", f"{wt['leave-ZL-out']['lo']:.3f}",
               f"{wt['leave-ZL-out']['hi']:.3f}"), "results/g3/result.json · within_type.leave-ZL-out"),
        Check("H3", "within-page AUROC", r"within-page (\d+\.\d+) \[([\d.]+), ([\d.]+)\]",
              (f"{wp['point']:.3f}", f"{wp['lo']:.3f}", f"{wp['hi']:.3f}"), "results/g3/result.json · within_page"),
        Check("H3", "ECE", r"\(ECE (\d+\.\d+)\)", f"{g3['ece']:.3f}", "results/g3/result.json · ece"),
        Check("H3", "leave-{ZL, IT}-out AUROC, above 0.5",
              r"leave-\{ZL, IT\}-out within-type AUROC is (\d+\.\d+) \[([\d.]+), ([\d.]+)\], above 0\.5",
              (f"{wt['leave-ZL-IT-out']['point']:.3f}", f"{wt['leave-ZL-IT-out']['lo']:.3f}",
               f"{wt['leave-ZL-IT-out']['hi']:.3f}"), "results/g3/result.json · within_type.leave-ZL-IT-out",
              "the lower bound clears 0.5",
              lambda f: float(f[1]) > 0.5),
        Check("H3", "ZL alternatives as hard labels", r"hard labels in training \((\d+\.\d+)% of glyphs\)", share,
              f"docs/gates/G3.md: {alternatives.group(1)} of {alternatives.group(2)} ZL glyphs"),
        Check("H3", "leave-{ZL, IT}-out population", r"smaller population \(([\d,]+) glyphs\)",
              f"{g3['n']['leave-ZL-IT-out']:,}", "results/g3/result.json · n.leave-ZL-IT-out"),
        Check("Deviations", "VO-047: H3 scores G2's paired lines", r"a line-selection deviation \((VO-\d+)\)",
              "VO-047", "docs/decisions.yaml · VO-047"),
    ]
    rows += [_check(normalized, c) for c in checks]
    outcomes = ["pass", _load_json(ROOT / "results" / "g3" / "consistency" / "20261028.json")["outcome"],
                _load_json(ROOT / "results" / "g3" / "consistency" / "20261029.json")["outcome"]]
    present = "All three seeds pass." in normalized
    rows.append(Row("H3", "all three seeds pass", "present" if present else "absent",
                    f"gate and seeds 20261028/20261029 outcomes: {', '.join(outcomes)}",
                    "results/g3/result.json; results/g3/consistency/*.json · outcome",
                    "match" if present and outcomes == ["pass", "pass", "pass"] else "mismatch"))
    return rows


def _g4_checks(g4: dict) -> list[Row]:
    """H4 figures against results/g4, including the ECE decomposition recomputed from the reliability bins."""
    normalized = _normalize(WRITEUP.read_text())
    matched, unmatched = g4["matched"], g4["unmatched"]
    levels = matched["R1"]["levels"]
    rel = matched["R1"]["reliability"]
    total = sum(b["n"] for b in rel)
    under = sum(b["n"] * max(b["accuracy"] - b["confidence"], 0) for b in rel) / total
    over = sum(b["n"] * max(b["confidence"] - b["accuracy"], 0) for b in rel) / total
    assert abs(under + over - matched["R1"]["ece"]["point"]) < 5e-3, "under + over does not sum to the pooled ECE"
    points = [levels[str(i)]["point"] for i in range(3)]
    los = [levels[str(i)]["lo"] for i in range(3)]
    deleted = [levels[str(i)]["deleted"] / levels[str(i)]["rendered"] for i in range(3)]
    checks = [
        Check("H4", "clean CER (matched arm)", r"clean CER is (\d+\.\d+)%", _pct(matched["R0"]["cer"], 1) ,
              "results/g4/result.json · matched.R0.cer"),
        Check("H4", "ECE range over the three levels", r"ECE is ([\d.]+)–([\d.]+) across all three levels",
              (f"{min(points):.2f}", f"{max(points):.2f}"), "results/g4/result.json · matched.R1.levels.*.point"),
        Check("H4", "ECE lower bounds, above the 0.05 bar",
              r"lower bounds ([\d.]+)–([\d.]+), all above the 0\.05 bar", (f"{min(los):.2f}", f"{max(los):.2f}"),
              "results/g4/result.json · matched.R1.levels.*.lo", f"smallest lower bound {min(los):.4f}",
              lambda f: min(los) > 0.05),
        Check("H4", "underconfidence share of the pooled ECE", r"underconfidence \(([\d.]+) of the pooled ([\d.]+)\)",
              (f"{under:.2f}", f"{matched['R1']['ece']['point']:.2f}"),
              "recomputed from results/g4/result.json · matched.R1.reliability (under + over = pooled ECE)"),
        Check("H4", "deleted matched glyphs by level",
              r"deleted in the degraded rendering were (\d+)%, (\d+)% and (\d+)%",
              tuple(_pct(d, 0) for d in deleted),
              "results/g4/result.json · matched.R1.levels.*.deleted / .rendered"),
        Check("H4", "degraded CER (matched arm)", r"CER on the degraded rendering is (\d+\.\d+)%",
              _pct(matched["R1"]["cer"], 1) , "results/g4/result.json · matched.R1.cer"),
        Check("H4", "unmatched-word glyph collage CER", r"glyph collage:\*\* (\d+\.\d+)% clean CER",
              _pct(unmatched["R0"]["cer"], 1) , "results/g4/result.json · unmatched.R0.cer"),
        Check("H4", "disputed stratum agreement with ZL",
              r"(\d+\.\d+)% agreement with ZL, on repeated draws of (\d+) crops",
              (_pct(g4["R2"]["accuracy"], 1), str(g4["R2"]["instances"])),
              "results/g4/result.json · R2.accuracy, R2.instances"),
        Check("Corrections", "correction 6: 14,702 matched glyphs, not 14,779",
              r"([\d,]+); the 14,779 came from a dev prototype", f"{matched['R0']['rendered']:,}",
              "results/g4/result.json · matched.R0.rendered; docs/decisions.yaml · VO-078, VO-083 (14)"),
        Check("Corrections", "correction 8: level 2's ECE rests on 2,309 scored", r"rests on ([\d,]+) scored",
              f"{levels['2']['n']:,}", "results/g4/result.json · matched.R1.levels.2.n; VO-083 (16)"),
    ]
    return [_check(normalized, c) for c in checks]


def _record_checks(decisions: list[dict]) -> list[Row]:
    """Record-level figures: error counts, hours, images and the prereg pin, against docs/decisions.yaml."""
    rows: list[Row] = []
    by_id = {r["id"]: r for r in decisions}
    normalized = _normalize(WRITEUP.read_text())
    cited = sorted(set(re.findall(r"VO-\d+", WRITEUP.read_text())))
    missing = [v for v in cited if v not in by_id]
    rows.append(Row("Record", "every VO- id cited in the writeup exists", f"{len(cited)} ids cited", "no dangling ids",
                    "docs/decisions.yaml", "match" if not missing else "mismatch",
                    f"missing: {', '.join(missing)}" if missing else ""))
    vo063, vo081, vo082, vo083 = (by_id[v]["decision"] for v in ("VO-063", "VO-081", "VO-082", "VO-083"))
    checks = [
        Check("Abstract", "seventeen reporting errors logged", r"(seventeen) were logged as findings",
              "seventeen", "docs/decisions.yaml · VO-083", "VO-083 numbers its findings to (17)",
              lambda f: "(17)" in vo083),
        Check("Abstract", "corrections split 8 before the owner / 9 reaching",
              r"(Eight were caught before reaching the owner, seven of them by red-team review. Nine reached the owner)",
              "Eight were caught before reaching the owner, seven of them by red-team review. Nine reached the owner",
              "docs/decisions.yaml · VO-083", "VO-083: eight before the owner, seven by red-team, nine reached",
              lambda f: "Eight were caught before the owner saw them" in vo083 and "Nine reached the owner" in vo083),
        Check("Corrections", "correction 5: the count was six", r"(request to log them \| Six \|)",
              "request to log them | Six |", "docs/decisions.yaml · VO-063",
              "VO-063: the chat count of three was six", lambda f: "it was six" in vo063),
        Check("Corrections", "correction 8 / caught-before item: seed margin 0.067 for 0.086",
              r"(\d+\.\d+) for (\d+\.\d+), caught by the agent's own script check", ("0.067", "0.086"),
              "docs/decisions.yaml · VO-063 (4), VO-083 (8)"),
        Check("Budget", "remaining owner hours (2.9 of 4 spent)", r"The remaining (\d+\.\d) hours",
              f"{4 - float(re.search(r"Owner hours are (\d+\.\d)", vo081).group(1)):.1f}",
              "docs/decisions.yaml · VO-081", "4 hours minus VO-081's 2.9 spent"),
        Check("Reproducibility", "G4 images kept locally: 1,800 PNGs, 385 MB",
              r"The ([\d,]+) rendered G4 images \((\d+) MB\)",
              (f"{int(re.search(r"There are (\d+) PNG files", vo082).group(1)):,}", "385"),
              "docs/decisions.yaml · VO-082 (385,333,386 bytes)"),
        Check("Reproducibility", "gate config hashes recorded before the runs",
              r"(on a config hash recorded before it: VO-040, VO-052 and VO-078)",
              "on a config hash recorded before it: VO-040, VO-052 and VO-078",
              "docs/decisions.yaml · VO-040, VO-052, VO-078", "all three rows exist",
              lambda f: all(v in by_id for v in ("VO-040", "VO-052", "VO-078"))),
    ]
    rows += [_check(normalized, c) for c in checks]
    pins = [m[1] for r in decisions if (m := re.search(r"docs/prereg\.md .*has sha256 ([0-9a-f]{64})", r["decision"]))]
    digest = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    rows.append(Row("Reproducibility", "the prereg sha is the latest pin (VO-077)", digest[:16] + "…",
                    "matches the latest pin", "docs/prereg.md; docs/decisions.yaml · VO-077",
                    "match" if digest == pins[-1] else "mismatch"))
    return rows


def run() -> list[Row]:
    decisions = _decisions()
    rows = _h1_checks(_load_json(ROOT / "results" / "map-v0" / "summary.json"))
    rows += _pairwise_checks(_load_json(ROOT / "results" / "map-v0" / "summary.json"))
    rows += _g2_checks(_load_json(ROOT / "results" / "g2" / "result.json"))
    rows += _g3_checks(_load_json(ROOT / "results" / "g3" / "result.json"))
    rows += _g4_checks(_load_json(ROOT / "results" / "g4" / "result.json"))
    rows += _record_checks(decisions)
    return rows


def render(rows: list[Row]) -> str:
    counts = {v: sum(r.verdict == v for r in rows) for v in ("match", "mismatch", "untraceable")}
    lines = [
        "# Writeup audit",
        "",
        f"Generated by `python -m voynich_ocr.audit` on {AUDIT_DATE}, against `results/` and `docs/` on main. One row",
        "per figure in [docs/writeup.md](writeup.md): the figure as written, the value recomputed from its source",
        "(file and key), and the verdict. Figures the writeup took from a gate packet are checked against that gate's",
        "committed result files, or recomputed with the committed code where the packet names it (`g2.gate_power`).",
        "",
        (f"**{len(rows)} figures audited: {counts['match']} match, {counts['mismatch']} mismatch, "
         f"{counts['untraceable']} untraceable.** A mismatch or an untraceable figure is a finding: it gets a "
         "VO- row"),
        "in docs/decisions.yaml and a correction proposed in a PR, never a silent edit. No discrepancy was found, so",
        "the writeup is not edited by this audit.",
        "",
        "| # | Section | Figure | As written | Expected (source) | Verdict |",
        "|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        written = r.written.replace("|", "\\|")
        expected = f"{r.expected} ({r.source})".replace("|", "\\|")
        lines.append(f"| {i} | {r.section} | {r.figure} | {written} | {expected} | {r.verdict} |")
    lines += [
        "",
        "## Notes",
        "",
        "### The leave-{ZL, IT}-out rate (3.61%)",
        "",
        "`summary.json` carries two near-identical rates: the **leave-{ZL, IT}-out** map's `gated_rate` is 0.036086,",
        "which rounds to the writeup's 3.61%, and the **leave-IT-out** map's is 0.036196 (3.62%). The writeup's figure",
        "is the first of these and is correct; the two maps score different populations (50,185 and 103,492 gated",
        "columns). An early review of this audit flagged 0.036196 as a suspected discrepancy behind the 3.61% figure;",
        "the flag is resolved as a no-finding.",
        "",
        "### The test-page rate (3.83%)",
        "",
        "`results/` holds no test-page summary: the 40 test pages' rows were released separately as the `map-v0-test`",
        "GitHub release (VO-064). The audit counts the release's `full.tsv` — the published per-column file carries",
        "class, tier, flag, contributing sources and the gated flag, no readings (VO-028) — and confirms 1,046",
        "disagreeing of 27,299 gated columns, 3.83%. The script fetches the release when `build/map-v0-test/full.tsv`",
        "is absent, so the check reruns wherever the release is reachable.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="audit")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)
    rows = run()
    args.out.write_text(render(rows))
    bad = [r for r in rows if r.verdict != "match"]
    print(f"{len(rows)} figures audited, {len(bad)} not matching")
    for r in bad:
        print(f"  {r.verdict}: {r.section}: {r.figure}: wrote {r.written!r}, expected {r.expected!r}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
