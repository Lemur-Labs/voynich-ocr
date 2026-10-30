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

### A6 — 2026-10-29 — H3, test-instance attrition

- **Change:** for H3, "test instances" in the attrition rule means what A3 defines for H2: the gated columns of
  paragraph-text loci (ZL locus types `P*`) on test pages that have their own page image. `scoring.void_for_attrition`
  applies to how many of those columns get at least one gated glyph. Page attrition counts all 40 test pages.
- **Reason:** H3 reads the same paragraph lines on the same pages as H2 (the W2 model is the W3 model, VO-047).
  Labels and foldout panels can never yield a glyph, so counting them would void H3 by construction, as it did for
  H2 before A3. Fixed before any G3 test-page statistic. Like A5, it comes after G2's test-page inference.

### A4 — 2026-10-29 — H4, glyph source and calibration on known text

- **Change 1, exemplars:** G2 killed clustering, so the collage no longer draws on cluster exemplars. An exemplar is
  a glyph instance from a non-test page whose recognized token equals the ZL reading of its column. Its crop is the
  W2 crop (VO-035) and its label is that token. Exemplars are drawn per token with seed 20261027. A token with no
  exemplar is rendered as a gap and counted.
- **Change 2, calibration:** besides CER, the report gives `scoring.ece` (15 bins) of the W3 model's glyph confidence,
  as H3 defines it with H3's temperature, against correctness on the rendered text. A recognized glyph is correct when
  a unit-cost alignment places it on an identical rendered glyph; insertions are incorrect, and deletions are
  counted. The interval is a 95% bootstrap over rendered lines, with seed 20261027. A reliability curve is reported.
- **Change 3, claims:** the G4 row of "Claims allowed" gains a permission: "the recognizer's confidence is calibrated
  on synthetic Naibbe ink" only when the ECE interval's upper bound is ≤0.05. A row cannot say "calibrated" about the
  manuscript.
- **Unchanged:** there is no threshold on CER and no kill. H4 stays a bound on synthetic ink.
- **Reason:** with clustering killed, the arm's remaining value is a check of the pipeline on text with a known
  answer (VO-044). Calibration on known text is the one test there where the ground truth isn't a transliteration.
  The exemplars use ZL-agreeing instances because a mislabelled exemplar would render the wrong glyph, and the error
  would be charged to the recognizer.
- **Not added:** HOG against DINOv2. Features play no part in rendering or recognition, so there's nothing for them
  to be compared on in H4. HOG's G2 result stays an exploratory note (VO-044).

### A7 — 2026-10-30 — H4, degraded known-answer glyphs and a disputed stratum

- **Text:** the plaintext is `input/examples/nathist_book16.txt` from Greshko's repository at the vendored commit.
  - **Encipherment:** it is enciphered once by the vendored `naibbe.py` with its defaults, under the wrapper with
    Python's `random` seeded to 20261027. The output is taken without the 3% space removal.
  - **Lines:** its words are wrapped, in order, into lines of 9 words, and the first 600 lines are rendered.
- **Renderings:** H4 makes three renderings of the same enciphered text, each exactly once:
  - **R0, clean:** A4's exemplars, every glyph at level 0;
  - **R1, degraded:** R0's exemplar draws, each glyph at a drawn level;
  - **R2, disputed:** disputed exemplars where available, at level 0.
- **Exemplar draws:** A4's "drawn per token" means one draw per rendered glyph, with replacement, from the pool of
  that glyph's token.
- **How a draw is made:** every draw is one `rng.random()` value u.
  - **From a pool:** a pool of n instances is ordered by (page, locus, column), and the draw takes item floor(un).
  - **Level:** floor(3u).
  - **No pool:** a glyph whose token has no pool still consumes its u.
- **Random streams:** `numpy.random.SeedSequence(20261027).spawn(6)` gives six streams. In order, they are for
  exemplar, level, band, disputed, bootstrap and spacing. Each stream is consumed in line order, then glyph order.
  - Every rendered glyph takes one exemplar draw.
  - In R1, every rendered glyph takes one level draw and one band draw, whatever its level.
  - In R2, every rendered glyph takes one disputed draw, whether or not its token has a disputed pool, and every
    word space takes one spacing draw.
- **Degradation operator:** applied to an exemplar's pixels before collage scaling.
  - **Pixels:** the RGB pixels of its cut's bounding box on the page image. This is the box `clusters.crop` takes
    before padding, so it has no padding or fill.
  - **Notation:** W and H are the box's width and height in pixels. b is the per-channel 90th percentile of the
    box's pixels before degradation (`numpy.percentile`, linear).
  - **Order of operations:**
    1. In floating point, fade each channel: I → b + a(I − b).
    2. Blur with `scipy.ndimage.gaussian_filter` (`sigma=(σ, σ, 0)`, so channels never mix; `truncate=4.0`;
       `mode="nearest"`).
    3. Set a full-height band of width w = rint(fW) to b. Its left edge is floor(u(W − w + 1)), with u the glyph's
       band draw.
    4. Clip to [0, 255] and round to uint8 with `numpy.rint`, once.
  - **Faint results:** a glyph left with no ink above b is still rendered and keeps its label.

  | Level | σ | a | f |
  |---|---|---|---|
  | 0 | 0 (no blur) | 1 | 0 |
  | 1 | 0.03H | 0.6 | 0.2 |
  | 2 | 0.06H | 0.35 | 0.4 |

  Levels are drawn uniformly. The label is always the enciphered token.
- **Collage:** each line of text becomes one image. All of the values below were set by the agent (VO-067), not
  carried over from A4 or H4.
  - **Placement:** boxes are pasted after degradation, at page resolution, with no rescaling or padding. They are
    placed left to right with their bottom edges aligned.
  - **Spacing in R0 and R1:** a word space is as wide as the median width of the line's boxes.
  - **Spacing in R2:** each word space's width is drawn from the gap pool, so these lines look like the manuscript.
    - **Gap pool:** the inter-word gaps on the validation pages' G2-paired rows. A gap is the horizontal distance
      from the right edge of the last instance's cut box before a ZL word space to the left edge of the first
      instance's box after it, both on that row. A negative gap counts as 0.
    - **Order:** the pool is ordered by (page, locus, column of the instance before the gap).
  - **Canvas:** the canvas has an 8 px margin on every side. It is filled with the per-channel median, over the
    line's boxes, of their b.
  - **Recognizer input:** the recognizer gets the whole canvas as the line polygon, with a horizontal baseline 8 px
    above its bottom edge.
- **Freeze:** before the first rendering:
  - a byte-exact fixture test of the operator is committed;
  - the config hash of the renderer and its inputs is recorded in `docs/decisions.yaml`.

  A rerun follows the prereg's bug-rerun rule, and the first result stays the headline.
- **Calibration (changes A4):** A4's ECE and its interval are computed on R1. Changes from A4:
  - ECE and its interval are also reported per level, with a reliability curve for each.
  - In the per-level figures, a recognized glyph takes the level of the rendered glyph the alignment places it on.
  - Insertions count only in the pooled figure.
  - Deleted rendered glyphs are counted per level, as A4 counts them, and are not in any ECE.
  - Each per-level interval resamples that level's glyphs, grouped by line, so no resample is empty.
  - **Bootstrap seeds:** the bootstrap stream spawns five children, used in this order:
    1. R1 pooled;
    2. level 0;
    3. level 1;
    4. level 2;
    5. R2.

    Each child is passed as `scoring.page_bootstrap`'s seed.
  - A4's permission, "calibrated on synthetic Naibbe ink", now needs the pooled upper bound **and every level's**
    upper bound to be ≤ 0.05. The claim names the three levels.
- **Power:** the levels are drawn uniformly, so each level gets about a third of the rendered glyphs. At about
  4.3 tokens per enciphered word (Greshko's shipped ciphertext, at ZL's 0.82 tokens per EVA letter), that is
  roughly 7,800 glyphs per level, about 13 per line. The table below comes from a simulation,
  `docs/prereg/a7_power.py` (seed 20261027, 200 simulations, 400 line resamples; arguments `600 13 0` and
  `600 13 0.1`).
  - **Model:** a uniform miss δ makes accuracy equal confidence minus δ. Two confidence distributions are used,
    Beta(8, 1) and U(0.2, 1).
  - **Line difficulty:** each line has its own accuracy shift. With a shift of SD 0 the glyphs are independent; SD
    0.1 models lines of different difficulty.

  | True uniform miss δ | P(level passes), SD 0 | P(level passes), SD 0.1 |
  |---|---|---|
  | 0 | 1.00 | 1.00 |
  | 0.02 | 1.00 | 0.94–0.98 |
  | 0.03 | 0.97–0.99 | 0.47–0.80 |
  | 0.04 | 0.41–0.64 | 0.05–0.27 |
  | 0.05 | 0.01–0.03 | 0.00–0.01 |

  - **What a pass means:** a level missing by 0.05 or more almost never passes, and one missing by 0.04 passes up
    to about two times in three. A pass does not show calibration is exact.
  - **What it cannot detect:** ECE cannot see errors that cancel within a bin, such as one token over-confident and
    another under-confident at the same confidence.
  - **The disputed stratum** has only tens of instances and no power statement. It is descriptive.
- **CER:** H4's CER, the bound, is computed on R0. CER on R1 is reported as descriptive and is not a bound. The clean
  CER is a bound on recognizer capacity, not a claim about the manuscript (VO-066).
- **Disputed stratum (R2, reported only, never gated):**
  - **Pool:** a token's pool is the glyph instances on **validation pages** in gated **disagree** columns of the
    full map, with H3's gated set as amended by A2. An instance enters only when ZL's reading of its column is
    exactly one token, which is the label. Tokens outside the codec are not used. The recognizer's reading plays
    no part.
  - **Draws:** with replacement, from the disputed stream.
  - **Glyphs with no disputed pool:** they use their R0 exemplar and are not scored.
  - **Scoring:** recognized glyphs aligned to a disputed glyph are scored. Insertions are not scored.
  - **Reported:** ECE and accuracy against the ZL label, the instance count, and a 95% bootstrap grouped by source
    instance, from the bootstrap stream's fifth child.
  - **What an error means:** disagreement with ZL, which may or may not be a misread of the ink.
  - **Where ZL and the model still enter:**
    - ZL is one of the sources that defines "disagree";
    - the crop boundaries are the recognizer's own spans;
    - T was fitted on these pages' ZL labels.
- **Unchanged:** A4's exemplar pool, its 15 bins, its bootstrap over rendered lines (now from the bootstrap
  stream), the gap rule for tokens with no exemplar, and no CER threshold or kill.
- **Reason:**
  - **Degradation:** A4's exemplars are glyphs the recognizer already reads as ZL does, and many come from training
    pages whose crops the model was trained on. Clean collage therefore tests calibration mostly where the model is
    confident. Degradation adds hard glyphs whose answer is still known (VO-060).
  - **Disputed stratum:** disputed sites are the hard glyphs that matter, but there the only label is a
    transliteration, so they are reported apart. They come from validation pages so that the model was not trained
    on their crops.
  - **Clean rendering:** R0 keeps H4's CER a bound on clean synthetic ink.
- **Fixed blind:** the levels, the text amount and the collage values were set before any crop was degraded and
  before any Naibbe text was rendered.

### A8 — 2026-10-30 — H4, word-level exemplars (declared deviation, found before any Naibbe rendering)

- **What kind of change this is:** a change to the instrument, found while calibrating the instrument. It is not a
  change to the hypothesis.
- **Evidence:** dev renders on non-Naibbe text, before any Naibbe rendering, showed the following:
  - **A7's glyph collage** read at **62–65% CER**, at level 0 on ZL token lines from training pages. That is 10
    lines, with and without masking outside the cut polygon.
  - **Real manuscript lines** read at **about 7%**: the G3 gate's CER against ZL on the test pages was 7.0%.
  - **A word-level collage** read at **14% CER** on 20 dev lines. That figure is optimistic: those lines were chosen
    so that every word had a word exemplar, which favours common words.
  - **Cause:** each glyph crop is a slice of the whole line polygon. It carries ink from its neighbours and from the
    lines above and below, and gluing slices together breaks the ligatures between glyphs.
- **Dev lines, excluded from everything scored:**
  - **Glyph collage:** f1r.1, f1r.2, f1r.3, f1r.7, f1r.8, f1r.13, f1r.15, f1r.16, f1r.22 and f1r.23.
  - **Word collage:** f2r.3, f2v.3, f2v.6, f3r.19, f3r.20, f4v.4, f5r.4, f6r.2, f6r.7, f6v.13, f6v.15, f8r.3,
    f8v.5, f8v.6, f8v.7, f8v.16, f9v.2, f9v.9, f10r.3 and f10r.8.
  - **Excluded folios:** f1r, f2r, f2v, f3r, f4v, f5r, f6r, f6v, f8r, f8v, f9v and f10r. No exemplar of any kind is
    drawn from these folios.
  - A 3-line smoke run of random codec tokens was also made, and is not scored.
- **Word exemplars:** a word exemplar is a run of glyph instances on one row of a training page. Training pages
  here means not test, not validation, and not an excluded folio. The run must:
  - lie between two ZL word spaces (`.` or `-`) or a row end;
  - have consecutive columns;
  - have each instance's recognized token equal to its column's ZL reading.

  Its crop is the bounding box of the union of its glyphs' cuts on the page image. Its label is its token sequence.
  A Naibbe word is **matched** when a word exemplar has exactly its token sequence, and **unmatched** otherwise.
- **Leakage and what the bound means:** word exemplars come only from training pages, never from test or validation
  pages. Every glyph in a word exemplar was read the way ZL reads it, so the clean arm inherits ZL's readings and
  ZL's segmentation. The clean CER is a bound on recognizer capacity given ZL's segmentation, not a claim about the
  manuscript (VO-066).
- **Draws:** `SeedSequence(20261027).spawn(7)` adds a seventh stream, `word`. A7's six streams are unchanged,
  because children are fixed by index.
  - Every word takes one `word` draw, matched or not.
  - A matched word's exemplar is item floor(un) of its pool. The pool is ordered by (page, locus, first column).
  - Every glyph still takes all of A7's draws.
  - An unmatched word uses A7's glyph exemplar draws, from A4's pool minus the excluded folios.
- **Degradation stays per glyph:** in R1, each glyph of a matched word is degraded inside the word crop at its own
  drawn level, by A7's operator.
  - **Glyph regions:** glyph i's region spans the full height of the crop. It runs from the left edge of its cut's
    box (or the crop's left edge, for the first glyph) to the left edge of the next glyph's cut box (or the crop's
    right edge, for the last glyph). Edges are clamped to be non-decreasing.
  - **Operator inputs:** b, W and H are those of the region.
  - **Never per word:** the word as a whole is never degraded at a single level.
- **Collage:** word crops are pasted whole, with A7's placement, canvas, margin and baseline. A7's word space, the
  median box width, uses the line's glyph regions and glyph boxes.
- **Arms and roles:**

  | Arm | Role |
  |---|---|
  | Matched-word glyphs | **Primary.** It carries H4's clean CER bound (R0) and the calibration verdict (R1: pooled and every level, A7's rule) |
  | Unmatched-word glyphs (A7's glyph collage) | **Reported only.** It cannot pass or fail anything |
  | R2 | Unchanged from A7 and reported only. It is a glyph collage, so its figures describe reading collaged crops |

  - **Arm attribution:**
    - An aligned recognized glyph belongs to its rendered glyph's arm.
    - An insertion belongs to the arm of the nearest rendered glyph before it in the alignment, or after it at the
      start of a line.
    - A deletion belongs to its rendered glyph's arm.
  - **An arm's CER:** its attributed substitutions, deletions and insertions, over its rendered glyph count.
- **Expected shares and power:**
  - **Expected shares:** on the 600-line text, 68% of words and 65% of glyphs are matched (14,779 of 22,891). That
    is about 4,930 matched glyphs per level, about 8 per line. The shares come from the word pool under these rules,
    counted on the text alone, with no rendering.
  - **Minimum:** each level needs at least **3,000 matched glyphs**. This is from `docs/prereg/a7_power.py` at
    600 lines × 5 glyphs.
    - At 3,000, a calibrated level (δ = 0) passes with probability 0.91–1.00.
    - A uniform miss of 0.05 passes with probability ≤ 0.01.
    - A uniform miss of 0.04 passes with probability 0.01–0.18.
  - **Below the minimum:** at 1,800 glyphs, a calibrated level passes with probability as low as 0.09, because
    ECE's upward bias then dominates. A level under 3,000 is reported as **underpowered**, and the results template
    says so. Such a level's failure doesn't count as evidence of miscalibration, and the calibration verdict cannot
    be "calibrated".
  - **At the expected count:** with about 4,800 matched glyphs per level, the simulated pass rates are:
    - δ = 0: 1.00;
    - δ = 0.04: 0.02–0.32;
    - δ = 0.05: 0.00–0.01.

    A pass rules out a uniform miss of 0.05 or more per level, as A7 states.
- **Unchanged:** A7's operator, levels, text, streams one to six, bootstrap, write-once and rerun rules, and R2.
