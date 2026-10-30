# Where Voynich transliterations disagree, and what a recognizer's confidence says about it

Draft for owner review · 2026-10-30 · Lemur-Labs/voynich-ocr · Code MIT, outputs CC BY 4.0

## Abstract

An AI agent (Claude) ran a pre-registered research program on the Voynich manuscript, with the owner reviewing at
four gates and spending 2.9 of a 4-hour budget.

- **How the program ran:**
  - **Failures by its own rule:** pre-registered tests failed by their own rules. The image-clustering test (H2) was
    killed, and the claim that the recognizer is calibrated on known-answer ink (H4) was refused.
  - **A declared instrument change:** mid-course, the synthetic-ink instrument was changed. The change was declared
    as an amendment before any data it affected (A8).
  - **Reporting errors:** seventeen were logged as findings. Eight were caught before reaching the owner, seven of
    them by red-team review. Nine reached the owner, in chat summaries or in one amendment figure, and each was
    corrected on the record.
- **Scientific results:**
  - **H1, disagreement map:** a per-glyph map of where five published transliterations disagree after STA
    conversion. 4.59% of gated columns disagree on the 187 non-test pages, and 3.83% on the 40 test pages.
  - **H2, image clusters:** the images did not explain the disagreements at this test's power.
  - **H3, recognizer confidence:** it predicts where transliterations disagree, beyond glyph type and page, under
    two declared amendments.
  - **H4, synthetic ink:** on synthetic Naibbe-cipher ink, the recognizer's clean CER is bounded at 13.4%, and its
    confidence is not calibrated.
- **Not claimed:** nothing here deciphers the text or says which reading is correct.

## Corrections

Every reporting error found is listed, with who caught it. Full entries are VO-063 and VO-083 in
`docs/decisions.yaml`.

**These reached the owner, and are corrected here:**

| # | What was said | Where | Caught by | Correct statement |
|---|---|---|---|---|
| 1 | Both k variants cleared their nulls (G2) | chat | red-team | Only HOG cleared its null; the k variants did not |
| 2 | A G3 smoke test was "still running" | chat | owner's question | It had hung at 0% CPU for about 2.5 hours |
| 3 | G3's pass depends on A5 only | chat | red-team | It depends on A5 and A6 |
| 4 | The seed spread's place in the prereg (G3) | chat | red-team | Reported beside the gated number, per forking paths |
| 5 | VO-063's errors numbered "three" | chat | owner | Six |
| 6 | A8 expected 14,779 matched glyphs | A8 text | renderer review | 14,702; the 14,779 came from a dev prototype (VO-078) |
| 7 | The 0.97 → 0.80 top bin belongs to the matched arm (G4) | chat | the agent, next message | It belongs to the unmatched arm |
| 8 | Every G4 level cleared the sample minimum | chat | packet red-team | The minimum counts rendered glyphs; level 2's ECE rests on 2,309 scored |
| 9 | G4 overconfidence appears only in level 2's top bin | chat | packet red-team | It appears at level 1 above about 0.77, and at level 2 from about 0.5 up |

**These were caught before reaching the owner:**
- the G3 packet's label-blind "kill" (it is void);
- VO-053's two missing readings;
- the Naibbe check overstated as reproducing his script;
- A8's claim missing "training-page ink";
- three G4 packet overstatements: a deletion cause stated as fact, R2's caveats missing, and a single untested cause;
- G3's seed margin, 0.067 for 0.086, caught by the agent's own script check.

**Other defects:**
- The map post owed since G1 was dropped until the owner asked.
- An edit left `docs/decisions.yaml` unparseable on main for one merge; a parse test now guards it.

## Deviations from the pre-registration

All are appended to `docs/prereg.md` (append-only) or recorded in `docs/decisions.yaml` before the data they
affect.

| Id | What changed | When, relative to data |
|---|---|---|
| A1, A2 | H3's coverage minimum fixed at 0.72; gated columns need 3 contributing sources after the mask | At G1, before any test-page figure |
| A3, A6 | Attrition counts readable paragraph columns, not labels or foldouts (H2, H3) | Before each gate run, on validation dry runs |
| VO-035 | Glyph crops from CTC frame gaps instead of kraken's cuts | After a validation dry run killed, before test inference |
| VO-041 | ZL helped choose the scored test lines in G2 (36 pages). Recorded as a deviation; the kill stands, and a label-blind split is reported | Found at G2 review, after the gate run |
| VO-047 | H3 scores the same G2-paired lines; the label-blind subset is reported | Before any G3 test inference |
| A5 | H3's coverage minimum re-fixed at 0.56. **Declared deviation**: the model had read test pages for G2. Under A1's 0.72, G3 would be void | After G2's test inference, before any G3 statistic |
| A4 | Naibbe glyph source after G2 killed clustering; ECE on known text added | Before any Naibbe rendering |
| A7 | Degraded known-answer glyphs; a disputed stratum, reported only | Before any Naibbe rendering |
| A8 | Word-level exemplars replace glyph collage. **Declared deviation**: the glyph collage read at 62–65% CER on dev lines, against about 7% on real lines. A change to the instrument found while calibrating it, not to the hypothesis | Before any Naibbe rendering; dev lines listed and excluded |

## Results

### H1: disagreement map (G1, pass)

- **What it is:** five transliterations (Zandbergen ZL, Takahashi IT, v101 GC, FSG FG, Currier–D'Imperio CD) are
  converted to STA, then to stroke tokens, and aligned per glyph.
- **Headline:** on gated columns (tier ≥3, at least 3 contributing sources, agree or disagree, no ZL alternative),
  **4.59%** disagree (5,509 of 119,921) on 187 non-test pages. Leaving ZL out gives 4.15%, leaving ZL and IT out
  3.61%, and the {ZL, IT, GC} map 2.68%. The 40 test pages, released after G3, give 3.83% (1,046 of 27,299).
- **Largest single pattern:** FSG's three minims before a final stroke where other sources write two, about 1,000
  columns. a/o differences appear in every source.
- **Releases:** `map-v0` and `map-v0-test` carry, per column, the class, tier, flags and contributing sources, with
  no readings (VO-028). `make snapshot map` rebuilds the full files from the sources.
- **Allowed claim:** "where the published transliterations disagree, per glyph and per page, after STA conversion".

### H2: image clusters (G2, kill)

- **Statement (VO-042):** "kill by the pre-agreed rule; the images do not explain the disagreements at this test's
  power". That is "not shown", not "shown absent".
- **Numbers:** the gated within-ZL-token entropy gap is 0.057, 95% CI [−0.017, 0.128], against a null of 0.058. The
  rule detects a gap of 0.164 with 80% power. At the observed gap, the chance of passing was 2.4%.
- **Deviation:** VO-041. Seeds 20261028 and 20261029 also kill.
- **HOG:** HOG features cleared their null for the gate seed only, not for the others. That is an observation that
  didn't replicate, not a lead.

### H3: recognizer confidence (G3, pass)

- **Statement (VO-054):** "Passed, under amendments A5 and A6 (fixed after G2's test-page inference; void under A1's
  original 0.72 coverage minimum): recognizer confidence predicts where transliterations disagree, beyond glyph type
  and page".
- **Numbers:** within-type AUROC 0.694 [0.664, 0.746] against a baseline bar of 0.566; leave-ZL-out 0.688
  [0.658, 0.739]; within-page 0.746 [0.714, 0.772]. All three seeds pass.
- **Deviation:** VO-047. The label-blind subset has too little coverage to count.
- **Calibration (VO-061):** "calibrated against the majority of the non-ZL transcribers (GC, FG, CD), not against
  the ink; the model was trained on ZL" (ECE 0.012).
- **Independence:** "independent of ZL" holds only with G3.md's qualifiers. ZL trained the model, ZL helped choose
  the lines, and the leave-out maps drop ZL's readings, not its line pairing.

### H4: known-answer bound (G4, calibration claim refused)

- **Statement (VO-079):** "On synthetic Naibbe ink built from training-page word crops (matched-word glyphs), the
  recognizer's clean CER is 13.4%, an upper bound for this pipeline given ZL's segmentation, not a claim about the
  manuscript. Its confidence is not calibrated there: ECE is 0.13–0.18 across all three levels (lower bounds
  0.12–0.16, all above the 0.05 bar), mainly through underconfidence (0.13 of the pooled 0.14), though it is
  overconfident at high confidence under degradation."
- **Deviation:** A8, declared above.
- **What a pass would have meant (fixed before the run):**
  - A pass rules out a uniform miss of 0.05 or more per level, not 0.04.
  - ECE can't see cancelling errors within a bin.
  - The disputed stratum is descriptive.
- **Untested causes:** the temperature fitted on manuscript lines, and the training-page ink. Neither was tested, and
  there is no evidence to prefer one.
- **Reported only:**
  - Unmatched-word glyph collage: 60.7% clean CER.
  - The disputed stratum: 52.8% agreement with ZL, on 70 crops.

## Not claimed

- Any decipherment.
- Any statement of which reading is correct.
- That the map is a "noise floor" or "ground truth", or that the transliterations are independent.
- That the clusters are an alphabet.
- That the recognizer is calibrated against the ink.
- Any accuracy on the manuscript.

## Budget and engagement

- **Owner hours:** 2.9 of 4 (VO-081). The remaining 1.1 hours are this review and the 2026-11-23 score.
- **Outreach:** the agent drafted the outreach and the owner sends it from his own accounts (VO-006, VO-062). That
  covers the voynich.ninja map post, a note to René Zandbergen, and the buyer-test messages. [Owner: what was sent,
  and when.]
- **Engagement criterion:** a reply from outside Lemur-Labs that addresses the method or the results, by
  2026-11-23. [Pending.]

## Reproducibility

- **Hypotheses and runs:**
  - Each hypothesis had one gate run, on a config hash recorded before it: VO-040 (G2), VO-052 (G3) and VO-078
    (G4).
  - The results are in `results/g1` to `results/g4`.
  - Third-party inputs are fetched by script and pinned by sha256 (`snapshot/manifest.sha256`), never committed.
- **Rendered G4 images:** the 1,800 images (385 MB) are kept locally. Their digest is in VO-082.
- **The pre-registration:** `docs/prereg.md`. Its current sha is in VO-077, and a test checks it.

## AI assistance

The code, analyses, packets and this draft were produced by an AI agent (Claude) under the pre-registration. The
owner made every decision marked `by: brian` in `docs/decisions.yaml`. Red-team passes were run by separate agent
instances, and the record lists where they were skipped (G3.md).
