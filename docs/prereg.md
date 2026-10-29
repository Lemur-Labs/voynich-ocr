# Pre-registration

Status: **frozen at KDP-F, 2026-10-27**, with E1–E5 as approved (`docs/gates/KDP-F.md`). The SHA-256 of this file
as frozen is recorded in `docs/decisions.yaml` (VO-021). A change is an appended amendment (date, section, reason),
never an edit. Gate outcomes are computed by the functions named here, in
`src/voynich_ocr/scoring.py`, and not judged.

## Inputs

- Third-party bytes: `snapshot/manifest.sha256`.
- Held-out pages: `docs/prereg/splits.json`, written by `python -m voynich_ocr.splits` (seed 20261027).
  - **40 test pages**, stratified by illustration type and Currier language, drawn from the 202 pages ZL, IT, GC and
    FG all cover.
  - **12 validation pages** drawn from the rest.
- Every random draw is seeded. The bootstrap and permutation nulls use B = 2000 and seed 20261026
  (`scoring.BOOTSTRAP_*`).

## Sources and their dependence

- **The five sources:** ZL, IT, GC, FG and CD, each in Zandbergen's published STA conversion.
- **Excluded:** RF (an automatic ZL+GC merge) and VT (IT under another name), because neither is a separate reading.
- **Not independent:** the five are not independent transcriptions. All are Zandbergen IVTFF editions, converted by
  his rules, and ZL and IT agree far more often than any other pair (`docs/gates/KDP-F.md`, item 2).
- **Dependence diagnostic:** G1 publishes the pairwise disagreement matrix as one.
- **Wording:** the map is described as *disagreement between published transliterations*, never as disagreement
  between independent transcribers, and never as a noise floor.

## Blind

- **No test-page metric or view:** no metric is computed on test pages, and no test-page image is viewed by an agent,
  before that hypothesis's gate run.
- **Map v0 withholds test pages:** the G1 map is computed and checked in full, but published with the 40 test pages'
  rows withheld until G3.
- **Configs frozen before test inference:** every W2 and W3 config (ketos arguments, the blla post-filter, the
  line-to-locus rule, the crop transform, k) is committed and its hash recorded in `docs/decisions.yaml` before any
  test-page inference.
- **One gate run per hypothesis:** exactly one model is evaluated on test pages, and each hypothesis gets one gate run.
- **Bug reruns:** a rerun needs a failing test on non-test data, committed before the rerun. The original result stays
  the headline, and the rerun is reported as a labelled sensitivity analysis.

## Units and alignment

- **Token:** one token is the `STA-aaa.bit` string of one STA code (pinned by hash). It is never an individual
  stroke. Full-STA comparison is a sensitivity analysis.
- **Files:** CD and GC use their level-0 files, `CD2a_0` and `GC2a_0`.
- **Spaces:** word spaces `.` and `,` are removed before alignment. Word-break disagreement is reported as its own
  map and is never part of glyph disagreement.
- **Alignment:**
  - Per locus, progressive alignment in the order ZL, IT, GC, FG, CD.
  - Each new sequence is aligned against the column-majority profile, with unit costs and ties broken leftmost.
  - A run of n `?` is one wildcard that matches 0..n columns at cost 0.
  - Columns inside a run of identical tokens are merged before disagreement is computed, so where a gap falls in an
    i-string doesn't matter.
  - Leave-out maps are re-aligned without the left-out sources.
- **Fixture:** a frozen fixture of 10 hand-built loci with expected columns is committed with the aligner, and its
  test must pass before G1.

## H1 — Disagreement map (W1, G1)

- **Disagreement:** a column disagrees when its contributing sources' readings are not all identical. A gap counts as
  a reading.
- **Tier:** a column's tier is the number of sources covering it, counted before any exclusion.
- **Excluded columns:**
  - *`?` columns:* a column where any source reads `?` is excluded from both classes and reported as a third class.
  - *ZL alternatives:* where ZL reads an alternative `[a:b]`, the first option is used and the column is flagged
    `zl_uncertain`. Flagged columns are reported but excluded from every gated set.
- **Expressibility mask:**
  - Evaluated per source at the STA-code level.
  - A source is dropped from a column when a competing reading is an STA code that source's file never produces.
  - A gap-versus-token disagreement where one side is CD or FG is reported as a separate class: `granularity`.
- **Outputs:**
  - per-column records;
  - per-page rates;
  - per-section rates over the fixed set {ZL, IT, GC, FG} only;
  - pairwise disagreement matrices;
  - leave-one-source-out, leave-ZL-out and leave-{ZL, IT}-out maps;
  - a {ZL, IT, GC} robustness map;
  - the word-break map.
- **G1 passes when** all four hold:
  - `make map` is byte-identical on two runs.
  - The parser's text extraction matches `ivtt -x2` on all five native files, apart from the documented `!`-locator
    divergence.
  - The alignment fixture passes.
  - The injected-perturbation test recovers every injected disagreement and reports none on unperturbed copies.
- **G1 kills** only if the data can't be parsed.

## H2 — Image clusters explain disagreement beyond the token (W2, G2)

- **Crops:**
  - *Primary:* greedy CTC label runs (the H3 span definition) from the single W2 Kraken model, trained on ZL labels
    from non-test, non-validation pages.
  - *Control:* a label-free proposer (connected components on the binarized line), scored only on lines where its
    crop count equals the column count.
- **Crop transform:** pad to square with background, then resize to 224 px. Fixed before any test inference.
- **Features:** frozen DINOv2 ViT-S/14 (Apache-2.0), L2-normalized. A HOG control arm is reported, not gated.
- **Clustering:** k-means with k = 2 × the number of distinct tokens in the training labels, seed 20261027. Results
  for k × {0.5, 4} are reported, not gated.
- **Gated statistic:**
  - The **within-ZL-token entropy gap**, `scoring.within_stratum_gap` over `scoring.loo_cluster_entropy`.
  - Cluster entropy excludes every instance from the same page.
  - Computed on test-page instances in columns of tier ≥3.
  - The interval comes from `scoring.page_bootstrap`, and the null is `scoring.permutation_null` (`disagree`
    shuffled within each page).
- **Baseline, reported:** the same scorer with clusters replaced by the ZL token. By construction it has no
  within-token signal, and it shows what the text alone gives.
- **Gate:** `scoring.decide_clusters` passes when the gap's lower bound exceeds the null's 97.5th percentile.
  - If the control arm's point estimate has the opposite sign, the gate narrows: the primary result is reported with
    that caveat.
  - The gate is void, not killed, when `scoring.void_for_attrition` holds for test pages or test instances.

## H3 — Recognizer confidence predicts disagreement beyond type and page (W3, G3)

- **Model:**
  - Kraken 7.1.1, CTC, trained from scratch on ZL labels from non-test, non-validation pages, `ketos -r train`.
  - **Three training seeds** (20261027, 20261028, 20261029). The gate uses seed 20261027, and the spread across seeds
    is reported.
  - The W2 model is the W3 model. One model reaches test pages.
- **Decoding:** greedy decoding, with no beam.
- **Glyph confidence:**
  1. Take the full per-frame posteriors (`return_logits=True`).
  2. Apply temperature T.
  3. A glyph's span is the maximal run of frames whose argmax is its emitted class.
  4. Its confidence is the maximum over that span of the emitted class's posterior.
  5. Kraken's built-in `confidences` is not used.
- **Temperature:** T minimizes CTC loss on the validation pages' ZL labels, on a grid from 0.50 to 5.00 in steps of
  0.05.
- **Mapping to the map:**
  - Each recognized line is aligned to its locus's column-consensus string: the majority reading per column, with
    gaps removed. Ties are broken in source order.
  - An aligned glyph inherits that column's class.
  - Inserted glyphs are excluded and counted.
- **Gated set:** test-page glyphs in columns of tier ≥3, excluding `?`, `zl_uncertain` and `granularity` columns.
  Test loci containing alternatives are kept.
- **Statistics,** all bootstrapped by page:
  - **within-type AUROC** of 1 − confidence, `scoring.within_type_auroc`, on the full map and the leave-ZL-out map;
  - **within-page AUROC**, `scoring.within_page_auroc`, on the full map.
- **Baselines** on the same glyphs:
  - B1: the token's disagreement rate on non-test pages;
  - B2: −log of the token's frequency in the training labels;
  - B3: the token's stroke count;
  - B4: span width in frames;
  - B5: the page's mean confidence.
  - B4 and B5 vary within a token and are scored with `scoring.within_type_auroc` on the full map; the larger point
    estimate is the **within-type baseline bar**. B1–B3 are constant within a token and are reported pooled only.
- **Gate:** `scoring.decide_recognizer`.
  - **Pass:** the full-map within-type lower bound exceeds both 0.5 and the within-type baseline bar, the
    leave-ZL-out within-type lower bound is >0.5, and the within-page lower bound is >0.5.
  - **Narrow:** the full-map conditions hold, but the leave-ZL-out condition does not.
  - **Kill:** anything else.
  - **Void:** when `scoring.void_for_attrition` holds, or when `scoring.void_for_underpower` holds for either
    `scoring.within_type_coverage` or `scoring.within_page_coverage` on the gated set.
  - **Coverage minimum:** `scoring.MIN_GROUP_COVERAGE` is fixed at G1 from non-test pages, by an appended amendment,
    before any test-page inference. Until then the gate refuses to run.
- **Reported, not gated:**
  - the pooled AUROC, `scoring.auroc_statistic`, beside each baseline's pooled AUROC;
  - the leave-{ZL, IT}-out within-type AUROC;
  - `scoring.ece` of top-1 confidence against agreement with the leave-{ZL, IT}-out column majority, with 15 bins;
  - CER against ZL and against the column majority.

## H4 — Known-answer bound (W4, G4)

- **Cipher:** Greshko's `naibbe-cipher`, vendored at a pinned commit with attribution and a citation. The RNG is
  wrapped and seeded.
- **Port check:**
  - Decrypting the shipped ciphertexts reproduces the shipped respaced plaintexts.
  - `decrypt(encrypt(p))` round-trips for 100 seeds.
- **Rendering:** the plaintexts are enciphered, mapped Eva → STA → AAA, and rendered by glyph collage. The exemplars
  come from **non-test pages only**, and each cluster is assigned its majority reading.
- **Report:** the W3 model's CER on the rendered lines, as a bound on synthetic ink. No threshold.

## Claims allowed per outcome

| Outcome | May say | May not say |
|---|---|---|
| G1 pass | "where the published transliterations disagree, per glyph and per page, after STA conversion" | "noise floor", "ground truth", "independent transcriptions", any statement of which reading is correct |
| G2 pass | "image clusters separate disputed from undisputed instances of the same transliterated glyph" | "the clusters are the true alphabet" |
| G3 pass | "recognizer confidence predicts where transliterations disagree, beyond glyph type and page" | "calibrated", unless ECE ≤ 0.05; "independent of ZL", unless the leave-{ZL, IT}-out lower bound is >0.5 |
| G3 narrow | "confidence tracks disagreement with ZL-trained conventions" | "predicts transcriber disagreement" |
| G4 | "CER on synthetic Naibbe ink, an upper bound for this pipeline" | any accuracy claim about the manuscript |

The kickoff's calibration kill criterion is restated here (VO-008). The kickoff text stands as written, and this
section governs.

## Engagement and owner hours

- The owner posts map v0 after G1 (VO-006).
- Engagement fails if, by 2026-11-23, no reply from an account outside Lemur-Labs addresses the method or the results.
- The owner self-reports hours at each gate. Over 4.0 kills the project.

## Forking paths

Each gated statistic has exactly one definition, given above. Sensitivity analyses can never replace a gated number.
These are reported beside it:

- full-STA comparison;
- the {ZL, IT, GC} map;
- the leave-{ZL, IT}-out map;
- the k variants;
- HOG;
- the control proposer;
- the seed spread.

## Amendments

### A1 — 2026-10-27 — H3, coverage minimum

- **Change:** `scoring.MIN_GROUP_COVERAGE = 0.72`.
- **Reason:** H3 fixes this value at G1 from non-test pages. 200 draws of 40 pages, seed 20261031, from the 162
  non-test pages all fixed sources cover, on the gated set after A2. The 5th percentiles are 0.727 within type and
  0.792 within page. At 0.72, 4.5% of draws void. The G1 packet proposed 0.80 from the gated set before A2; on the
  set after A2, 0.80 voids 22% of draws. The owner chose 0.72 to keep the stated rule: H3 voids only when the test
  set is less scorable than about 95% of same-size non-test sets.

### A2 — 2026-10-27 — H1, H2 and H3 gated sets

- **Change:** a gated column also needs at least 3 contributing sources after the expressibility mask, beside tier
  ≥3.
- **Reason:** without it, a tier-3 column can be left with 2 sources. On non-test pages these disagreed 90.5% of the
  time (2,602 of 2,874 columns), mostly ZL against GC over GC's `d5`. That is disagreement by construction, the
  mirror of the agreement by construction the tier rule prevents. The non-test headline moves from 6.61% to 4.59%.
  No test-page figure has been computed.

### A3 — 2026-10-29 — H2, test-instance attrition

- **Change:** for H2, "test instances" in the attrition rule means the gated columns of paragraph-text loci (ZL locus
  types `P*`) on test pages that have their own page image. `scoring.void_for_attrition` is applied to how many of
  those columns get at least one gated instance. Page attrition is unchanged. It counts all 40 test pages, so the 4
  foldout test pages excluded by VO-030 count as lost.
- **Reason:** the H2 pipeline reads only paragraph lines on pages with their own image. Labels and foldout panels can
  never yield an instance, so counting them made the gate void by construction. On the validation pages, which were
  dry-run only, 2,343 of 4,608 gated columns were covered (51%). Of the 2,475 readable columns, 2,343 were covered
  (94.7%). No test-page figure has been computed, and no test page has been segmented or read.

### A5 — 2026-10-29 — H3, coverage minimum re-fixed on the scored pipeline (declared deviation)

- **Change:** `scoring.MIN_GROUP_COVERAGE = 0.56`, replacing A1's 0.72.
- **Reason:** A1's rule is that H3 voids only when the test set is less scorable than about 95% of same-size
  non-test sets. A1 measured coverage on the whole map, with the column majority standing in for the recognizer's
  glyph. H3 scores only the gated glyph instances the W2 pipeline yields: paragraph lines on pages with their own
  image, with the recognized token as the type. On that population, `g1.pipeline_coverage` makes 200 draws of 36
  pages, seed 20261031, from the 135 non-test pages with gated instances in `build/instances`. Those instances come
  from the gate model (seed 20261027) with G2's pairing (VO-047). 36 is the 40 test pages less the 4 without their
  own image (VO-030). As in A1, the cutoff is the 5th percentile of the lower of the two coverages per draw, 0.567,
  rounded down. At A1's 0.72, 39.5% of draws void; at 0.56, 3.5% (`g1.write_pipeline_coverage`, `results/a5/coverage.json`).
- **Deviation:** H3 fixes the minimum before any test-page inference. The W2/W3 model had already read the test
  pages for G2, as the prereg provides. No G3 coverage or other G3 statistic had been computed on test pages when
  A5 was fixed. The owner kept A5 as a declared deviation (VO-048).
