# Draft amendment A4: H4, glyph source and calibration on known text

Status: **appended** to `docs/prereg.md` on the owner's approval (VO-057), before any Naibbe rendering.

### A4 — H4, glyph source and calibration on known text

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
