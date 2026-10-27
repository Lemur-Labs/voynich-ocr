# G1 image spot-check

20 loci from `spot-check-sample.json` (seed 20261031, one per non-test page), viewed by a fresh Sonnet agent on Yale
IIIF images of those 20 pages only. Reported, not gated.

| Verdict | Columns |
|---|---|
| ambiguous (image supports competing readings) | 16 |
| one_clear (transcriber error or convention) | 4 |
| alignment_artifact | 1 |
| cannot_tell (line not located: rings, labels, foldouts) | 21 |

- The artifact (f15v.7 col 0–1) is the unit, not the aligner. ZL's `{co}` ligature is one STA code, and the others
  write c and o as two, so one physical pair yields two disputed columns.
- one_clear: f15v.7 col 1 (ligature convention), f52v.1 col 10 (IT and FG drop a minim), f79v.30 cols 4 and 29
  (FG adds a minim).
- GC's d5 (v101 `7`/`6`) against d0 was judged image-unresolvable. It is a convention difference.
- Unchecked: f71r, f78r, f82r, f82v, f86v3, f102r2, f68v1, f70v1. The agent couldn't place those lines.

| locus | line_found | column | verdict | reason |
|---|---|---|---|---|
| f102r2.10 | no | 21 | cannot_tell | not located |
| f104r.4 | yes | 2 | ambiguous | smudged bench stroke on sh; GC encodes a different stroke order |
| f104r.4 | yes | 10 | ambiguous | ordinary d; GC "7" form (d5) not resolvable |
| f104r.4 | yes | 25 | ambiguous | open-topped a, could be a or c |
| f112v.44 | yes | 4 | ambiguous | small bowl glyph after ch is a/o-like |
| f112v.44 | yes | 29 | ambiguous | ordinary d; d5 variant not resolvable |
| f112v.44 | yes | 32 | ambiguous | round o-like mark before p-gallows, faint |
| f15v.7 | yes | 0 | alignment_artifact | ZL `{co}` ligature in col 1 leaves col 0 empty |
| f15v.7 | yes | 1 | one_clear | separate c and o visible; ligature is ZL convention |
| f15v.7 | yes | 19 | ambiguous | hooked s/r shape |
| f28r.5 | yes | 14 | ambiguous | extra curl on final r; GC r-variant plausible |
| f30r.2 | yes | 15 | ambiguous | GC's two looped-gallows variants not resolvable |
| f42r.20 | yes | 19 | ambiguous | shol vs chol |
| f51v.1 | yes | 13 | ambiguous | sh vs s+e segmentation |
| f51v.1 | yes | 14 | ambiguous | same cluster as col 13 |
| f52v.1 | yes | 10 | one_clear | three minims + n hook (iiin); IT and FG drop one |
| f52v.1 | yes | 28 | ambiguous | r vs s |
| f68r1.4 | unsure | 7 | ambiguous | crowded minims, 2 or 3 |
| f68v1.4 | no | 8, 9 | cannot_tell | panel not identified |
| f69r.3 | yes | 6 | ambiguous | compound gallows vs c+t |
| f70v1.6 | unsure | 2 | cannot_tell | label not found |
| f71r.12 | unsure | 12, 13, 19, 34, 38, 66, 69, 72 | cannot_tell | rotated ring text |
| f71v.13 | unsure | 3 | cannot_tell | stroke too faint |
| f78r.21 | no | 0, 3, 17 | cannot_tell | not located |
| f79v.30 | yes | 4 | one_clear | "in", FG's third minim looks wrong |
| f79v.30 | yes | 29 | one_clear | same |
| f79v.30 | yes | 37 | ambiguous | GC k-variant |
| f82r.29 | no | 7, 27 | cannot_tell | not located |
| f82v.45 | no | 1 | cannot_tell | not located |
| f86v3.31 | no | 3, 24 | cannot_tell | not located |
