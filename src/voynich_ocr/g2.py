import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from voynich_ocr import clusters, lines, proposer, scoring, segment
from voynich_ocr import disagreement as d
from voynich_ocr.instances import OUT as INSTANCES
from voynich_ocr.snapshot import ROOT

FROZEN = [
    "src/voynich_ocr/segment.py", "src/voynich_ocr/lines.py", "src/voynich_ocr/runner.py",
    "src/voynich_ocr/recognize.py", "src/voynich_ocr/instances.py", "src/voynich_ocr/proposer.py",
    "src/voynich_ocr/clusters.py", "src/voynich_ocr/g2.py",
]  # fmt: skip
K_VARIANTS = (0.5, 4)
OUT = ROOT / "results" / "g2"


def config_hash(model: Path) -> str:
    h = hashlib.sha256()
    for rel in FROZEN:
        h.update(rel.encode() + b"\0" + (ROOT / rel).read_bytes())
    h.update(hashlib.sha256(model.read_bytes()).digest())
    return h.hexdigest()


def _load(pages: list[str]) -> tuple[list[dict], dict[str, np.ndarray]]:
    metas, feats = [], {"dinov2": [], "hog": []}
    for page in pages:
        f = INSTANCES / f"{page}.json"
        if not f.exists():
            continue
        metas += json.loads(f.read_text())["instances"]
        z = np.load(clusters.OUT / "features" / f"{page}.npz")
        for name, parts in feats.items():
            parts.append(z[name].reshape(-1, z[name].shape[-1] if z[name].size else 1))
    return metas, {k: np.concatenate([x for x in v if x.size]) for k, v in feats.items()}


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


def _arm(fit_x: np.ndarray, eval_x: np.ndarray, eval_metas: list[dict], k: int) -> dict:
    gated = np.array([m["gated"] for m in eval_metas], dtype=bool)
    if not gated.any() or len(fit_x) < k:
        return {"n": int(gated.sum())}
    labels = clusters.fit(fit_x, k).predict(eval_x)
    return gap_test(labels[gated], [m for m, g in zip(eval_metas, gated, strict=True) if g])


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
    out["primary"] = _arm(fit_x["dinov2"], eval_x["dinov2"], eval_metas, k)
    out["hog"] = _arm(fit_x["hog"], eval_x["hog"], eval_metas, k)
    out["k_variants"] = {str(f): _arm(fit_x["dinov2"], eval_x["dinov2"], eval_metas, round(f * k)) for f in K_VARIANTS}
    gated = [m for m in eval_metas if m["gated"]]
    tokens = {t: i for i, t in enumerate(sorted({m["zl"] for m in gated}))}
    out["baseline_zl_token"] = gap_test(np.array([tokens[m["zl"]] for m in gated]), gated)
    inputs = d.load()
    by_id = {lo.id: lo for lo in inputs.loci}
    model = clusters.dinov2()
    cx_fit, _ = _control(fit_pages, inputs, by_id, model)
    cx_eval, cm_eval = _control(eval_pages, inputs, by_id, model)
    out["control"] = _arm(cx_fit, cx_eval, cm_eval, k)
    out["attrition"] = attrition(eval_pages, eval_metas, inputs)
    gap = scoring.Interval(out["primary"]["gap"], out["primary"]["lo"], out["primary"]["hi"])
    # Narrowing needs a control estimate of the opposite sign; an empty control arm has none, so it cannot narrow.
    control = out["control"].get("gap", gap.point)
    decision = scoring.decide_clusters(gap, out["primary"]["null_975"], control)
    out["outcome"] = "void" if out["attrition"]["void"] else decision
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="g2")
    p.add_argument("model", type=Path)
    p.add_argument("--gate", action="store_true", help="score test pages: the one G2 gate run")
    args = p.parse_args(argv)
    if args.gate:
        digest = config_hash(args.model)
        if digest not in (ROOT / "docs" / "decisions.yaml").read_text():
            raise SystemExit(f"config hash {digest} is not recorded in docs/decisions.yaml")
    result = run(args.model, args.gate)
    out = OUT if args.gate else ROOT / "build" / "g2-dry"
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=1) + "\n")
    print(result["outcome"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
