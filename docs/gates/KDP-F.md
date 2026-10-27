# KDP-F — Formulation gate

2026-10-27 · Owner review target: 15 min · On approval, W1 starts Oct 31 (launch: "run W1 per docs/plan.md and docs/prereg.md")

## Your calls

| # | Decision | Recommendation |
|---|---|---|
| E1 | **Change the H3 gated statistic** from pooled AUROC (VO-008) to: within-type AUROC on the full and leave-ZL-out maps, within-page AUROC on the full map, and a pooled AUROC that beats five trivial baselines. "Narrow" then permits only the sentence "tracks disagreement with ZL-trained conventions" | **Accept.** The pooled AUROC passes on glyph type or page quality alone (`tests/test_scoring.py` demonstrates both on synthetic data). Without this change, a pass means nothing |
| E2 | The red-team also proposed a fixed bar: lower bound ≥ 0.60 | **Reject.** 0.60 is arbitrary. Beating the baselines is the bar that carries meaning, and E1 already requires it |
| E3 | **Map v0 withholds the 40 test pages** until G3 | **Accept.** It costs the post nothing (187 of 227 pages remain) and keeps the blind intact |
| E4 | The **leave-{ZL, IT}-out** arm is reported, not gated. It decides whether the writeup may say "independent of ZL" | **Accept.** ZL and IT agree far more than any other pair. Gating on a two-source map would be underpowered |
| E5 | **Freeze `docs/prereg.md`** with E1–E4 applied (it's already drafted that way) | **Accept.** The hash is recorded in `decisions.yaml` once you say yes |

Please also report your owner hours so far. I can't measure them.

## Decided without you (overturn any)

| Row | Outcome |
|---|---|
| VO-010 | Recognizer outputs STA-AAA. Mapping verified by S1, decided by the VO-005 rule |
| VO-011 | Kraken 7.1.1 CTC, Python 3.12, full posteriors |
| VO-012 | DINOv2 ViT-S/14 (Apache-2.0), not DINOv3 (gated, pass-through license); HOG control |
| VO-013 | Default blla segmentation + post-filter. A page whose line count doesn't match its loci is excluded |
| VO-014 | Own IVTFF parser; `ivtt` used as a local oracle and never vendored (it has no license) |
| VO-015 | Make + artifacts + Zenodo; glyph-collage synthetic hand |
| VO-016 | Naibbe: vendor Greshko's own Python (MIT, citation requested) |

## Red-team review of the draft (fresh Opus agent, artifacts only)

| # | Finding | Disposition |
|---|---|---|
| 1 | Glyph type alone can give AUROC > 0.5 | Fixed: within-type gated statistic, baselines B1–B4 (E1) |
| 2 | Sources aren't independent. ZL–IT normalized edit rate ≈ 0.023, every other pair 0.030–0.074 | Fixed: dependence matrix at G1; "independent" banned; leave-{ZL, IT}-out arm (E4) |
| 3 | Comparison unit and alignment underspecified | Fixed: token = per-code aaa string, spaces removed, level-0 files, profile alignment, `?` wildcard, merged identical runs, frozen fixture |
| 4 | Dropping `?` hides the hardest glyphs; low tiers are "agree" by construction | Fixed: tier ≥3 counted before exclusions; `?` as a third class; `granularity` class |
| 5 | A lower bound > 0.5 is no bar; "narrow" undefined | Fixed with E1 and the claims table. 0.60 bar rejected (E2) |
| 6 | Page quality confounds the pooled AUROC | Fixed: within-page AUROC is gated; B5 page-mean baseline |
| 7 | Mean posterior over a CTC span measures glyph width | Fixed: max over the greedy label run; B4 width baseline |
| 8 | Clusters restate ZL labels | Fixed: within-ZL-token gap; leave-out over the whole page; token baseline |
| 9 | Pipeline forking paths; test-page attrition | Fixed: configs hashed before test inference; one model; 3 seeds; void at >25% attrition |
| 10 | The blind leaks through map v0 | Fixed: E3; bug reruns need a failing test first |
| 11 | The entropy-gap null isn't zero | Fixed: within-page permutation null, 97.5th percentile |
| 12 | The writeup could overreach | Fixed: claims-allowed table; exemplars from non-test pages only; RF/VT exclusion stated |

## State

- F0 artifacts: `docs/spikes/` S1–S6, `docs/plan.md` (trade studies re-scored), `docs/prereg.md`, `docs/prereg/splits.json`.
- Code: `src/voynich_ocr/{snapshot,scoring,splits}.py`. 27 tests, CI green.
- Each scorer has an injected-effect test and a null or confound test. A mutation that removes the leave-out step was
  caught.
- Infra: GCP project `lemur-voynich-ocr` with a $200 budget alerting at 25/50/100%, and bucket
  `gs://lemur-voynich-ocr-snapshot` (7.4 MB). No compute has run.
- Known risk: test pages include rosette and astronomical pages (e.g. f68r2, f86v6) that segmentation will likely
  drop. Attrition is reported, and the gate voids past 25%.
