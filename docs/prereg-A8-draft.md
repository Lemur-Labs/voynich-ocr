# Amendment A8: H4, word-level exemplars

Status: **appended** to `docs/prereg.md` on the owner's approval (VO-075), before any Naibbe text was rendered.

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

  Its crop is the bounding box of the union of its glyphs' cuts on the page image. Like A7's glyph boxes, it is not
  masked to the cut polygons. Its label is its token sequence. A Naibbe word is **matched** when a word exemplar has
  exactly its token sequence, and **unmatched** otherwise.
  - **Uncertain spaces:** ZL's uncertain space `,` does not end a word.
  - **Pool order:** pages sort as strings (so f10r comes before f1r), then by locus, then by first column, which is
    unique within a locus.
- **Leakage and what the bound means:** word exemplars come only from training pages, never from test or validation
  pages. Every glyph in a word exemplar was read the way ZL reads it, so the clean arm inherits ZL's readings and
  ZL's segmentation. The clean CER is a bound on recognizer capacity given ZL's segmentation, not a claim about the
  manuscript (VO-066).
  - **Training-page ink:** the primary arm is entirely ink from training pages, which the model was trained on.
    A8 amends the G4 row of "Claims allowed" accordingly:
    - **The bound may be stated as** "CER on synthetic Naibbe ink built from training-page word crops (matched-word
      glyphs), an upper bound for this pipeline".
    - **The permission becomes** "the recognizer's confidence is calibrated on synthetic Naibbe ink built from
      training-page word crops".
- **Other pools:**
  - **Pages:** the glyph-collage fallback pool (A4's), R2's disputed pool and the gap pool may still use
    validation pages, since the owner's exclusion covers word exemplars. Every pool drops the excluded folios.
  - **Config hash:** the hash recorded before rendering covers the code, including the excluded-folio list, and the
    instances from which all pools are built.
- **Draws:** `SeedSequence(20261027).spawn(7)` adds a seventh stream, `word`. A7's six streams are unchanged,
  because children are fixed by index.
  - Every word takes one `word` draw, matched or not.
  - A matched word's exemplar is item floor(un) of its pool. The pool is ordered by (page, locus, first column).
  - Every glyph still takes all of A7's draws.
  - An unmatched word uses A7's glyph exemplar draws, from A4's pool minus the excluded folios.
  - **R2 fallback:** in R2, "their R0 exemplar" means the glyph's A4 crop from its exemplar draw, even inside a
    matched word. A glyph with neither a disputed nor an A4 exemplar is a gap in R2 and is counted.
- **Degradation stays per glyph:** in R1, each glyph of a matched word is degraded inside the word crop at its own
  drawn level, by A7's operator.
  - **Glyph regions:** glyph i's region spans the full height of the crop. It runs from the left edge of its cut's
    box (or the crop's left edge, for the first glyph) to the left edge of the next glyph's cut box (or the crop's
    right edge, for the last glyph). Edges are clamped to be non-decreasing.
  - **Operator inputs:** b, W and H are those of the region.
  - **Zero-width regions:** a region clamped to zero width renders nothing, and its glyph stays in the text.
  - **Never per word:** the word as a whole is never degraded at a single level.
- **Collage:** word crops are pasted whole, with A7's placement, canvas, margin and baseline. A7's word space and
  canvas fill use one width and one b per glyph piece: its region for a matched glyph, its box for an unmatched one.
  Zero-width regions are left out.
- **Arms and roles:**

  | Arm | Role |
  |---|---|
  | Matched-word glyphs | **Primary.** It carries H4's clean CER bound (R0) and the calibration verdict (R1: pooled and every level, A7's rule) |
  | Unmatched-word glyphs (A7's glyph collage) | **Reported only.** It cannot pass or fail anything |
  | R2 | Unchanged from A7 and reported only. It is a glyph collage, so its figures describe reading collaged crops |

  - **Alignment:** the alignment is A4's unit-cost alignment, backtracked from the end of the line. Ties prefer the
    diagonal (a match or substitution), then a deletion, then an insertion.
  - **Arm attribution:**
    - An aligned recognized glyph belongs to its rendered glyph's arm.
    - An insertion belongs to the arm of the nearest rendered glyph before it in the alignment, or after it at the
      start of a line.
    - A deletion belongs to its rendered glyph's arm.
  - **An arm's CER:** its attributed substitutions, deletions and insertions, over its rendered glyph count.
  - **The primary pooled R1 ECE** includes the matched arm's insertions. Per-level figures leave insertions out,
    as in A7.
- **Expected shares and power:**
  - **Expected shares:** on the 600-line text, 68% of words and 65% of glyphs are matched (14,779 of 22,891). That
    is about 4,930 matched glyphs per level, about 8 per line. The shares come from the word pool under these rules,
    counted on the text alone, with no rendering.
  - **Minimum:** each level needs at least **3,000 rendered matched glyphs**. The count comes from the text and the
    level stream alone, before any rendering, and is recorded with the config hash. The minimum is from
    `docs/prereg/a7_power.py` at 600 lines × 5 glyphs.
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
