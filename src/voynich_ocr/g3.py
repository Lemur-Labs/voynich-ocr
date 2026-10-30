import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from voynich_ocr import disagreement as d
from voynich_ocr import freeze, g2, instances, lines, recognize, scoring, segment
from voynich_ocr.align import majority
from voynich_ocr.instances import OUT as INSTANCES
from voynich_ocr.snapshot import ROOT, sha256

OUT = ROOT / "results" / "g3"
TEMPERATURE = ROOT / "build" / "g3" / "temperature.json"
GRID = tuple(round(0.5 + 0.05 * i, 2) for i in range(91))
MAPS = ("full", "leave-ZL-out", "leave-ZL-IT-out")
ECE_BINS = 15
_STROKE = re.compile(r"[a-z][0-9]")


def strokes(token: str) -> int:
    return len(_STROKE.findall(token))


def _ctc(posterior: np.ndarray, target: list[int], temperature: float) -> float:
    import torch

    logp = torch.from_numpy(recognize.log_posteriors(posterior, temperature).T[:, None, :])
    return float(torch.nn.functional.ctc_loss(
        logp, torch.tensor([target]), torch.tensor([logp.shape[0]]), torch.tensor([len(target)]),
        blank=recognize.BLANK, reduction="sum",
    ))  # fmt: skip


def fit_temperature(posteriors: list[np.ndarray], targets: list[list[int]], grid: tuple = GRID) -> dict:
    """The grid temperature with the least summed CTC loss; lines whose labels no path through their frames can
    emit have infinite loss at every temperature and are dropped."""
    kept = [(p, t) for p, t in zip(posteriors, targets, strict=True) if np.isfinite(_ctc(p, t, 1.0))]
    loss = {str(T): sum(_ctc(p, t, T) for p, t in kept) for T in grid}
    best = min(grid, key=lambda T: loss[str(T)])
    return {"temperature": best, "lines": len(kept), "dropped": len(targets) - len(kept), "loss": loss}


def glyphs(posterior: np.ndarray, temperature: float, l2c: dict) -> list[dict]:
    hot = np.exp(recognize.log_posteriors(posterior, temperature))
    return [{"char": l2c[(c,)], "confidence": conf, "frames": e - s} for c, s, e, conf in recognize.spans(hot)]


def disagreement_rates(instances_dir: Path, pages: list[str]) -> tuple[dict[str, float], float]:
    """B1: per recognized token, the share of its gated instances on `pages` in disagreeing columns, and the pooled
    share for tokens never seen there."""
    seen: dict[str, list[bool]] = {}
    for page in pages:
        f = instances_dir / f"{page}.json"
        if not f.exists():
            continue
        for m in json.loads(f.read_text())["instances"]:
            if m["gated"]:
                seen.setdefault(m["token"], []).append(m["class"] == "disagree")
    pooled = [x for v in seen.values() for x in v]
    return {t: float(np.mean(v)) for t, v in seen.items()}, float(np.mean(pooled))


def surprisal(root: Path, tokens: dict[str, str]) -> dict[str, float]:
    """B2: −log of each token's frequency among the training labels' tokens."""
    counts = Counter()
    for line in (root / "train.txt").read_text().split():
        counts.update(ch for ch in (ROOT / line).with_suffix(".gt.txt").read_text().strip() if ch != lines.SPACE)
    total = sum(counts.values())
    return {tokens[ch]: float(-np.log(n / total)) for ch, n in counts.items()}


def cer(pairs: list[tuple[list[str], list[str]]]) -> float:
    """Summed edit distance of each (recognized, reference) pair over the summed reference length."""
    return sum(recognize._distance(r, ref) for r, ref in pairs) / sum(len(ref) for _, ref in pairs)


def read(model, page: str, ids: list[str], instances_dir: Path) -> dict:
    """The page's row pairs, G2's stored ones and the label-blind ones, and the paired rows' posteriors at T = 1."""
    rows = segment.page_lines(json.loads((segment.OUT / f"{page}.json").read_text()), segment.height(page))
    pairs = json.loads((instances_dir / f"{page}.json").read_text())["pairs"]
    sizes = [im.size for _, im in lines.line_images(page, {str(i): r for i, r in enumerate(rows)})]
    blind, _ = instances.pair_rows_blind(sizes, ids)
    needed = sorted(set(pairs.values()) | set(blind.values()))
    return {"pairs": pairs, "blind": blind,
            "posteriors": dict(zip(needed, recognize.posteriors(model, page, [rows[i] for i in needed]), strict=True))}  # fmt: skip


def place(
    page: str, loci: list[d.Locus], pairs: dict[str, int], posteriors: dict, temperature: float,
    inputs: d.Inputs, l2c: dict, tokens: dict[str, str],
) -> tuple[dict[str, list[dict]], dict[str, int], list[dict]]:  # fmt: skip
    """Glyphs at `temperature` on one page's paired rows, aligned separately to each map's column consensus; the
    insertions per map; and each line's recognized, ZL and full-map consensus tokens for CER."""
    read_lines = {}
    for locus in loci:
        if locus.id in pairs:
            row = glyphs(posteriors[pairs[locus.id]], temperature, l2c)
            read_lines[locus.id] = [{**g, "token": tokens[g["char"]]} for g in row if g["char"] != lines.SPACE]
    every = [g["confidence"] for row in read_lines.values() for g in row]
    page_confidence = float(np.mean(every)) if every else float("nan")
    by_map: dict[str, list[dict]] = {name: [] for name in MAPS}
    inserted = dict.fromkeys(MAPS, 0)
    texts = []
    for locus in loci:
        if locus.id not in read_lines:
            continue
        row = read_lines[locus.id]
        recognized = [g["token"] for g in row]
        for name in MAPS:
            cols, where, n = instances.columns_for(locus, recognized, inputs, d.MAPS[name])
            inserted[name] += n
            if name == "full":
                cons = [t for t, _ in recognize.consensus([c.readings for c in cols])]
                texts.append({"recognized": recognized, "zl": instances.zl_tokens(inputs, locus.id), "majority": cons})
            for g, k in zip(row, where, strict=True):
                if k is None:
                    continue
                c = cols[k]
                by_map[name].append({
                    "page": page, "locus": locus.id, "column": k, "token": g["token"], "confidence": g["confidence"],
                    "frames": g["frames"], "page_confidence": page_confidence, "class": c.cls, "tier": c.tier,
                    "gated": c.gated, "majority": majority(list(c.readings.values())),
                })  # fmt: skip
    return by_map, inserted, texts


def _arrays(metas: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return (np.array([m["page"] for m in metas]), np.array([m["class"] == "disagree" for m in metas]),
            np.array([m["token"] for m in metas]))  # fmt: skip


def _interval(statistic, pages: np.ndarray) -> dict:
    i = scoring.page_bootstrap(statistic, pages)
    return {"point": i.point, "lo": i.lo, "hi": i.hi}


def _gated(metas: list[dict]) -> list[dict]:
    return [m for m in metas if m["gated"]]


def coverage(metas: list[dict]) -> dict:
    pages, disagree, types = _arrays(_gated(metas))
    return {"within_type": scoring.within_type_coverage(disagree, types),
            "within_page": scoring.within_page_coverage(disagree, pages)}  # fmt: skip


def statistics(by_map: dict[str, list[dict]], b1: dict[str, float], b1_pooled: float, b2: dict[str, float]) -> dict:
    """H3's statistics on each map's gated glyphs. A glyph's type is its recognized token; higher scores mean more
    likely disputed. B4 and B5 are scored both ways, higher and lower values as disputed, and the bar is the larger
    within-type point of the four (VO-050)."""
    out: dict = {"n": {name: len(_gated(by_map[name])) for name in MAPS}, "within_type": {}}
    for name in ("leave-ZL-out", "leave-ZL-IT-out"):
        metas = _gated(by_map[name])
        pages, disagree, types = _arrays(metas)
        unsure = 1 - np.array([m["confidence"] for m in metas])
        out["within_type"][name] = _interval(scoring.within_type_auroc(unsure, disagree, types), pages)
    full = _gated(by_map["full"])
    pages, disagree, types = _arrays(full)
    unsure = 1 - np.array([m["confidence"] for m in full])
    out["within_type"]["full"] = _interval(scoring.within_type_auroc(unsure, disagree, types), pages)
    out["within_page"] = _interval(scoring.within_page_auroc(unsure, disagree, pages), pages)
    out["pooled"] = _interval(scoring.auroc_statistic(unsure, disagree), pages)
    scores = {
        "B1": np.array([b1.get(t, b1_pooled) for t in types]),
        "B2": np.array([b2.get(t, np.inf) for t in types]),
        "B3": np.array([strokes(t) for t in types], dtype=float),
    }
    out["baselines"] = {k: {"pooled": _interval(scoring.auroc_statistic(s, disagree), pages)} for k, s in scores.items()}
    within = {"B4": np.array([m["frames"] for m in full], dtype=float),
              "B5": np.array([m["page_confidence"] for m in full])}  # fmt: skip
    for k, s in within.items():
        ways = {"higher": s, "lower": -s}
        out["baselines"][k] = {
            "pooled": {w: _interval(scoring.auroc_statistic(v, disagree), pages) for w, v in ways.items()},
            "within_type": {w: _interval(scoring.within_type_auroc(v, disagree, types), pages) for w, v in ways.items()},
        }
    out["baseline_bar"] = max(v["point"] for k in within for v in out["baselines"][k]["within_type"].values())
    loo = _gated(by_map["leave-ZL-IT-out"])
    # A merged column holds a run of one token, and the consensus aligns each glyph to one token of that run.
    agree = [bool(m["majority"]) and all(t == m["token"] for t in m["majority"]) for m in loo]
    out["ece"] = scoring.ece(np.array([m["confidence"] for m in loo]), np.array(agree), ECE_BINS)
    wt = {k: scoring.Interval(**v) for k, v in out["within_type"].items()}
    out["outcome_by_rule"] = scoring.decide_recognizer(
        wt["full"], wt["leave-ZL-out"], scoring.Interval(**out["within_page"]), out["baseline_bar"]
    )
    return out


def decide(
    by_map: dict[str, list[dict]], eval_pages: list[str], inputs: d.Inputs, b1: dict, b1_pooled: float, b2: dict
) -> dict:
    """Void on page or readable-column attrition (docs/prereg.md A6, A3's readable columns) or on either coverage under
    the minimum; otherwise the pre-registered rule."""
    out = {"attrition": g2.attrition(eval_pages, by_map["full"], inputs), "coverage": coverage(by_map["full"])}
    if out["attrition"]["void"] or any(scoring.void_for_underpower(c) for c in out["coverage"].values()):
        return {**out, "outcome": "void"}
    out.update(statistics(by_map, b1, b1_pooled, b2))
    out["outcome"] = out.pop("outcome_by_rule")
    return out


def _evaluate(reads: dict, key: str, temperature: float, inputs, loci: dict, l2c: dict, tokens: dict) -> dict:
    by_map = {name: [] for name in MAPS}
    inserted = dict.fromkeys(MAPS, 0)
    texts = []
    for page, r in reads.items():
        m, n, t = place(page, loci[page], r[key], r["posteriors"], temperature, inputs, l2c, tokens)
        for name in MAPS:
            by_map[name] += m[name]
            inserted[name] += n[name]
        texts += t
    cers = {ref: cer([(t["recognized"], t[ref]) for t in texts]) if texts else None for ref in ("zl", "majority")}
    return {"by_map": by_map, "inserted": inserted, "cer": cers, "lines": len(texts)}


def run(
    model_path: Path, gate: bool, instances_dir: Path | None = None, report: Path | None = None, fit: Path | None = None
) -> dict:
    """`fit` fits T on the validation pages into that directory; `report` scores the test pages with the T stored
    there, reported only (VO-056)."""
    store = instances_dir is None
    instances_dir = instances_dir or INSTANCES
    split = json.loads(d.SPLITS.read_text())
    eval_pages = sorted(split["test"] if gate or report else split["validation"])
    inputs = d.load()
    by_id = {lo.id: lo for lo in inputs.loci}
    paragraph = lines.paragraph_loci()
    loci = {p: [by_id[k] for k in paragraph.get(p, []) if k in by_id] for p in eval_pages}
    table = json.loads((lines.OUT / "codec.json").read_text())
    tokens = {ch: t for t, ch in table.items()}
    model = recognize.load(model_path)
    codec = model.net.codec
    reads = {
        p: read(model, p, [lo.id for lo in loci[p]], instances_dir)
        for p in eval_pages if (instances_dir / f"{p}.json").exists()
    }  # fmt: skip
    if report:
        T = json.loads((report / TEMPERATURE.name).read_text())["temperature"]
    elif fit:
        record = {**temperature_record(fit_from(reads, inputs, table, codec), model_path),
                  "instances": str(instances_dir.resolve()), "instances_sha256": instances_digest(instances_dir)}  # fmt: skip
        (fit / TEMPERATURE.name).write_text(json.dumps(record, indent=1) + "\n")
        T = record["temperature"]
    else:
        T = temperature(gate, lambda: fit_from(reads, inputs, table, codec), model_path, store)
    b1, b1_pooled = disagreement_rates(instances_dir, b1_pages(instances_dir, set(split["test"]), eval_pages))
    b2 = surprisal(lines.OUT, tokens)
    label = "test" if gate else "test, reported only (VO-056)" if report else "validation (dry run, not a result)"
    main = _evaluate(reads, "pairs", T, inputs, loci, codec.l2c, tokens)
    out = {"eval": label, "temperature": T, "inserted": main["inserted"], "cer": main["cer"],
           "lines": main["lines"]}  # fmt: skip
    out.update(decide(main["by_map"], eval_pages, inputs, b1, b1_pooled, b2))
    blind_reads = {p: r for p, r in reads.items() if r["blind"]}
    blind = _evaluate(blind_reads, "blind", T, inputs, loci, codec.l2c, tokens)
    out["label_blind"] = {"pages": sorted(blind_reads), "inserted": blind["inserted"], "cer": blind["cer"],
                          "coverage": coverage(blind["by_map"]["full"])}  # fmt: skip
    if blind_reads:
        out["label_blind"].update(statistics(blind["by_map"], b1, b1_pooled, b2))
    return out


def b1_pages(instances_dir: Path, test: set[str], scored: list[str]) -> list[str]:
    return sorted(f.stem for f in instances_dir.glob("*.json") if f.stem not in test and f.stem not in scored)


def temperature_record(fit: dict, model_path: Path) -> dict:
    return {**fit, "model": str(model_path), "model_sha256": sha256(model_path)}


def instances_digest(instances_dir: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(instances_dir.glob("*.json")):
        h.update(f.name.encode() + b"\0" + f.read_bytes())
    return h.hexdigest()


def temperature(gate: bool, fit, model_path: Path, store: bool = True) -> float:
    """The stored T at the gate, and in any dry run once the gate has run; otherwise `fit()` is run, and stored only
    when `store`."""
    if gate or (OUT / "result.json").exists():
        return json.loads(TEMPERATURE.read_text())["temperature"]
    record = temperature_record(fit(), model_path)
    if not store:
        return record["temperature"]
    TEMPERATURE.parent.mkdir(parents=True, exist_ok=True)
    TEMPERATURE.write_text(json.dumps(record, indent=1) + "\n")
    return record["temperature"]


def fit_from(reads: dict, inputs: d.Inputs, table: dict[str, str], codec) -> dict:
    """T from the paired rows' ZL labels; lines with a `?` or a token outside the codec carry no label."""
    zl = inputs.sources["ZL"].loci
    posteriors, targets, unlabelled = [], [], 0
    for r in reads.values():
        for locus, row in r["pairs"].items():
            label = lines.tokens(zl.get(locus, []), inputs.aaa)
            if label is None or any(t not in table for t in label):
                unlabelled += 1
                continue
            posteriors.append(r["posteriors"][row])
            targets.append(codec.encode("".join(table[t] for t in label)).tolist())
    return {**fit_temperature(posteriors, targets), "unlabelled": unlabelled}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="g3")
    p.add_argument("model", type=Path)
    p.add_argument("--gate", action="store_true", help="score test pages: the one G3 gate run")
    p.add_argument("--instances", type=Path, help="G2's stored row pairs (default build/instances)")
    p.add_argument("--fit", type=Path, help="fit T on the validation pages into this directory, for --report")
    p.add_argument("--report", type=Path, help="score test pages into this directory with its T, reported only")
    args = p.parse_args(argv)
    if sum([args.gate, args.fit is not None, args.report is not None]) > 1:
        raise SystemExit("--gate, --fit and --report are exclusive")
    own = args.fit or args.report
    out = OUT if args.gate else args.report or (args.fit / "validation" if args.fit else ROOT / "build" / "g3-dry")
    if own is not None:
        if not own.resolve().is_relative_to((ROOT / "build").resolve()):
            raise SystemExit("reported runs and their fits write only under build/")
        if any(own.resolve().is_relative_to((ROOT / o).resolve()) for o in freeze.OUTPUTS):
            raise SystemExit(f"{own} is inside a frozen output directory")
        if args.instances is None:
            raise SystemExit("--fit and --report need the seed's own --instances")
    if args.fit:
        if (args.fit / TEMPERATURE.name).exists():
            raise SystemExit(f"{args.fit / TEMPERATURE.name} is already fitted")
        args.fit.mkdir(parents=True, exist_ok=True)
    if args.report:
        fitted = args.report / TEMPERATURE.name
        if not fitted.exists():
            raise SystemExit(f"no fitted temperature at {fitted}; run --fit {args.report} first")
        record = json.loads(fitted.read_text())
        if record.get("model_sha256") != sha256(args.model):
            raise SystemExit(f"{fitted} was fitted for another model")
        if not (args.report / "validation" / "result.json").exists():
            raise SystemExit(f"{fitted} has no validation run beside it; it was not made by --fit")
        if (record.get("instances"), record.get("instances_sha256")) != (
            str(args.instances.resolve()), instances_digest(args.instances)
        ):
            raise SystemExit(f"{fitted} was fitted on other instances than {args.instances}")
        freeze.require(args.model)
        with open(args.report / "result.json", "x") as f:
            f.write('{"status": "started"}\n')
    if args.gate:
        if args.instances is not None:
            raise SystemExit("the gate reads G2's stored pairs in build/instances; --instances is for dry runs")
        if (OUT / "result.json").exists():
            raise SystemExit("the G3 gate has run; its result stands")
        if not TEMPERATURE.exists():
            raise SystemExit(f"no fitted temperature at {TEMPERATURE}; run the validation dry run first")
        if json.loads(TEMPERATURE.read_text()).get("model_sha256") != sha256(args.model):
            raise SystemExit(f"{TEMPERATURE.name} was fitted for another model")
        freeze.require(args.model)
        OUT.mkdir(parents=True, exist_ok=True)
        with open(OUT / "result.json", "x") as f:
            f.write('{"status": "started"}\n')
    result = run(args.model, args.gate, args.instances, args.report, args.fit)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=1) + "\n")
    print(result["outcome"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
