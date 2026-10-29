import argparse
import json
import sys
from pathlib import Path

import numpy as np

from voynich_ocr import clusters, freeze, lines, proposer, scoring, segment
from voynich_ocr import disagreement as d
from voynich_ocr.instances import OUT as INSTANCES
from voynich_ocr.snapshot import ROOT

K_VARIANTS = (0.5, 4)
OUT = ROOT / "results" / "g2"


def _load(pages: list[str]) -> tuple[list[dict], dict[str, np.ndarray]]:
    metas, feats = [], {"dinov2": [], "hog": []}
    for page in pages:
        f = INSTANCES / f"{page}.json"
        if not f.exists():
            continue
        page_metas = json.loads(f.read_text())["instances"]
        metas += page_metas
        z = np.load(clusters.OUT / "features" / f"{page}.npz")
        for name, parts in feats.items():
            if len(z[name]) != len(page_metas):
                raise AssertionError(f"{page}: {len(z[name])} {name} rows for {len(page_metas)} instances")
            parts.append(z[name].reshape(-1, z[name].shape[-1] if z[name].size else 1))
    return metas, {k: np.concatenate([x for x in v if x.size]) if metas else np.empty((0, 1)) for k, v in feats.items()}


def gap_test(labels: np.ndarray, metas: list[dict]) -> dict:
    """The within-ZL-token entropy gap with its page-bootstrap interval and within-page permutation null."""
    pages = np.array([m["page"] for m in metas])
    disagree = np.array([m["class"] == "disagree" for m in metas])
    strata = np.array([m["zl"] for m in metas])
    readings = [list(m["readings"].values()) for m in metas]
    entropy = scoring.loo_cluster_entropy(labels, readings, pages)
    interval = scoring.page_bootstrap(scoring.within_stratum_gap(entropy, disagree, strata), pages)
    null = scoring.permutation_null(lambda dis: scoring.within_stratum_gap(entropy, dis, strata), disagree, pages)
    return {"gap": interval.point, "lo": interval.lo, "hi": interval.hi, "null_975": null, "n": len(metas)}


def _comparable(metas: list[dict]) -> bool:
    """Some ZL token has both disputed and undisputed instances, so the within-token gap has an estimate."""
    classes: dict[str, set[str]] = {}
    for m in metas:
        classes.setdefault(m["zl"], set()).add(m["class"])
    return any({"agree", "disagree"} <= c for c in classes.values())


def _arm(fit_x: np.ndarray, eval_x: np.ndarray, eval_metas: list[dict], k: int) -> dict:
    gated = np.array([m["gated"] for m in eval_metas], dtype=bool)
    scored = [m for m, g in zip(eval_metas, gated, strict=True) if g]
    if not _comparable(scored) or len(fit_x) < k:
        return {"n": len(scored)}
    labels = clusters.fit(fit_x, k).predict(eval_x.astype(np.float64))
    return gap_test(labels[gated], scored)


def _control(pages: list[str], inputs: d.Inputs, by_id: dict, model) -> tuple[np.ndarray, list[dict]]:
    crops, metas = [], []
    for page in pages:
        f = INSTANCES / f"{page}.json"
        if not f.exists():
            continue
        c, m = proposer.page_control(page, json.loads(f.read_text())["pairs"], inputs, by_id)
        crops += c
        metas += m
    return clusters.embed(model, crops), metas


def readable(columns, eval_pages: list[str], imaged: set[str], paragraph: dict[str, list[str]]) -> set:
    """Gated paragraph-text columns on evaluated pages that have their own image (docs/prereg.md amendment A3)."""
    loci = {k for page in set(eval_pages) & imaged for k in paragraph.get(page, [])}
    return {(c.locus, c.index) for c in columns if c.gated and c.locus in loci}


def attrition(eval_pages: list[str], metas: list[dict], inputs: d.Inputs) -> dict:
    """Pages of the evaluated set, and its readable gated columns, that end up with at least one gated instance."""
    columns, _ = d.build(inputs, d.MAPS["full"])
    wanted = readable(columns, eval_pages, set(segment.image_pages()), lines.paragraph_loci())
    got = {(m["locus"], m["column"]) for m in metas if m["gated"]}
    pages = {m["page"] for m in metas if m["gated"]}
    return {
        "pages": [len(pages), len(eval_pages)],
        "columns": [len(got & wanted), len(wanted)],
        "void": scoring.void_for_attrition(len(pages), len(eval_pages))
        or scoring.void_for_attrition(len(got & wanted), len(wanted)),
    }


def run(model_path: Path, gate: bool) -> dict:
    split = json.loads(d.SPLITS.read_text())
    excluded = set(split["test"]) | set(split["validation"])
    seg_pages = sorted(f.stem for f in INSTANCES.glob("*.json"))
    fit_pages = [p for p in seg_pages if p not in excluded]
    eval_pages = sorted(split["test"] if gate else split["validation"])
    _, fit_x = _load(fit_pages)
    eval_metas, eval_x = _load(eval_pages)
    k = clusters.k()
    out = {"k": k, "eval": "test" if gate else "validation (dry run, not a result)"}
    inputs = d.load()
    out["attrition"] = attrition(eval_pages, eval_metas, inputs)
    if out["attrition"]["void"]:
        out["outcome"] = "void"
        return out
    out["primary"] = _arm(fit_x["dinov2"], eval_x["dinov2"], eval_metas, k)
    out["hog"] = _arm(fit_x["hog"], eval_x["hog"], eval_metas, k)
    out["k_variants"] = {str(f): _arm(fit_x["dinov2"], eval_x["dinov2"], eval_metas, round(f * k)) for f in K_VARIANTS}
    gated = [m for m in eval_metas if m["gated"]]
    tokens = {t: i for i, t in enumerate(sorted({m["zl"] for m in gated}))}
    out["baseline_zl_token"] = gap_test(np.array([tokens[m["zl"]] for m in gated]), gated)
    by_id = {lo.id: lo for lo in inputs.loci}
    model = clusters.dinov2()
    cx_fit, _ = _control(fit_pages, inputs, by_id, model)
    cx_eval, cm_eval = _control(eval_pages, inputs, by_id, model)
    out["control"] = _arm(cx_fit, cx_eval, cm_eval, k)
    if "gap" not in out["primary"]:
        raise AssertionError(f"no primary estimate on {out['primary']['n']} gated instances that passed attrition")
    gap = scoring.Interval(out["primary"]["gap"], out["primary"]["lo"], out["primary"]["hi"])
    # Narrowing needs a control estimate of the opposite sign; an empty control arm has none, so it cannot narrow.
    control = out["control"].get("gap", gap.point)
    out["outcome"] = scoring.decide_clusters(gap, out["primary"]["null_975"], control)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="g2")
    p.add_argument("model", type=Path)
    p.add_argument("--gate", action="store_true", help="score test pages: the one G2 gate run")
    args = p.parse_args(argv)
    out = OUT if args.gate else ROOT / "build" / "g2-dry"
    if args.gate:
        if (OUT / "result.json").exists():
            raise SystemExit("the G2 gate has run; its result stands")
        freeze.require(args.model)
        OUT.mkdir(parents=True, exist_ok=True)
        with open(OUT / "result.json", "x") as f:
            f.write('{"status": "started"}\n')
    result = run(args.model, args.gate)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=1) + "\n")
    print(result["outcome"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
