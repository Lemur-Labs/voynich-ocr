# Draft amendment A7: H4, degraded known-answer glyphs and a disputed stratum

Status: **draft**, for the owner's approval of its text. VO-060 approved the design. It is appended to
`docs/prereg.md` before any Naibbe rendering, and no exemplar has been drawn, degraded or rendered.

### A7 — H4, degraded known-answer glyphs and a disputed stratum

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
- **Random streams:** `numpy.random.SeedSequence(20261027).spawn(5)` gives five streams. In order, they are for
  exemplar, level, band, disputed and bootstrap. Each stream is consumed in line order, then glyph order.
  - Every rendered glyph takes one exemplar draw.
  - In R1, every rendered glyph takes one level draw and one band draw, whatever its level.
  - In R2, every rendered glyph takes one disputed draw, whether or not its token has a disputed pool.
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
- **Collage:** each line of text becomes one image.
  - **Placement:** boxes are pasted after degradation, at page resolution, with no rescaling or padding. They are
    placed left to right with their bottom edges aligned.
  - **Spacing:** a word space is as wide as the median width of the line's boxes.
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
- **CER:** H4's CER, the bound, is computed on R0. CER on R1 is reported as descriptive and is not a bound.
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
- **Levels fixed blind:** the parameters above were set before any crop was degraded and before any Naibbe text
  was rendered.
