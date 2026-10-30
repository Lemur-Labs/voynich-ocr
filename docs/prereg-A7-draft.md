# Draft amendment A7: H4, degraded known-answer glyphs and a disputed stratum

Status: **draft**, for the owner's approval of its text. VO-060 approved the design. It is appended to
`docs/prereg.md` before any Naibbe rendering, and no exemplar has been drawn or rendered.

### A7 — H4, degraded known-answer glyphs and a disputed stratum

- **Change 1, degradation:** each rendered glyph's exemplar crop is degraded at one of three fixed levels before
  collage. The level is drawn uniformly per rendered glyph with seed 20261027. With h the crop's height and b its
  background, the 90th-percentile pixel value:

  | Level | Gaussian blur σ | Ink fade, I → b + a(I − b) | Occlusion, a full-height band of value b |
  |---|---|---|---|
  | 0 | none | a = 1 | none |
  | 1 | 0.03h | a = 0.6 | 20% of the crop's width |
  | 2 | 0.06h | a = 0.35 | 40% of the crop's width |

  Fade is applied, then blur, then occlusion. The band's left edge is uniform over the positions that keep it inside
  the crop, with the same seed. The label stays the enciphered token, so the answer is known at every level.
- **Change 2, calibration:** A4's ECE, its interval and its claim permission are computed on all rendered glyphs,
  every level pooled. ECE and its interval are also reported per level, with a reliability curve for each. Nothing
  else in A4's definition changes.
- **Change 3, CER:** H4's CER is computed on a second rendering of the same text with the same exemplar draws, every
  glyph at level 0. CER on the degraded rendering is reported beside it.
- **Change 4, disputed stratum (reported only, never gated):** a second rendering of the same text draws each
  token's exemplar from glyph instances on **validation pages** in gated **disagree** columns of the full map,
  labelled by ZL's reading of the column, whatever the recognizer read. Tokens with no such instance use an A4
  exemplar, and only glyphs rendered from a disputed instance are scored. A ZL reading outside the codec is not
  used. Degradation is level 0. ECE and accuracy against the ZL label are reported, with the instance count. The
  validation pages hold 73 such instances with a ZL reading, so the stratum is small. The writeup states that an error in this stratum
  means disagreement with ZL, not a misread of the ink, and that T was fitted on these pages' ZL labels.
- **Unchanged:** A4's exemplars for the gated rendering (non-test pages, recognized token equals ZL), its 15 bins, its
  bootstrap over rendered lines with seed 20261027, the gap rule for tokens with no exemplar, and no CER threshold
  or kill.
- **Reason:** A4's exemplars are glyphs the recognizer already reads as ZL does, so clean collage tests calibration
  only where the model is confident. Degradation adds hard glyphs whose answer is still known (VO-060). Disputed
  sites are the hard glyphs that matter, but there the only label is a transliteration, so they are reported apart.
  They come from validation pages because the model was trained on ZL's labels for the training pages' crops.
- **Levels fixed blind:** the parameters above were set before any crop was degraded or viewed and before any
  Naibbe text was rendered.
