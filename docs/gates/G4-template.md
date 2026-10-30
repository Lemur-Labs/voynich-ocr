# G4: known-answer bound (H4, A4, A7, A8) — results template

Fill the numbers from the single run's result file. The sentences under "What a pass means" are fixed by the
owner (2026-10-30) and appear in the packet and the writeup unchanged, whatever the outcome.

## Outcome, computed

Primary arm: matched-word glyphs (A8), entirely training-page ink. Each level needs at least 3,000 rendered
matched glyphs, counted before rendering. A level under that is marked
**underpowered**: its failure is not evidence of miscalibration, and the claim cannot be made.

| Quantity (matched-word glyphs) | Value | Glyphs | Rule |
|---|---|---|---|
| R0 CER, the bound | | | none |
| R1 ECE, pooled | | | upper bound ≤ 0.05 |
| R1 ECE, level 0 | | | upper bound ≤ 0.05; ≥ 3,000 glyphs or underpowered |
| R1 ECE, level 1 | | | upper bound ≤ 0.05; ≥ 3,000 glyphs or underpowered |
| R1 ECE, level 2 | | | upper bound ≤ 0.05; ≥ 3,000 glyphs or underpowered |
| Claim "calibrated on synthetic Naibbe ink built from training-page word crops" | | | all four ECE rows pass, no level underpowered |

## What a pass means

- A pass rules out a uniform miss of 0.05 or more per level, not 0.04.
- ECE can't see cancelling errors within a bin.
- The disputed stratum is descriptive.

## Reported beside it, never gated

| Quantity | Value |
|---|---|
| R0 CER (bound on recognizer capacity given ZL's segmentation, not a claim about the manuscript) | |
| Matched share of glyphs, expected 65% | |
| Unmatched-word glyphs (A7 glyph collage): R0 CER, R1 ECE pooled and per level | |
| R1 CER (descriptive, not a bound) | |
| Deleted rendered glyphs per level | |
| R2 ECE and accuracy against ZL, instance count | |
| Tokens rendered as gaps (no exemplar) | |
