# S4 - Segmentation sources (Voynich MS 408)

## Verdict
- Use Kraken default blla for LINE boxes. It is usable on text-heavy pages: f103r, f108v, f78r are close to line-correct (few merges, no systematic splitting). Needs a post-filter for false lines (star labels, margin marks, page numbers) and a manual QA pass on a sample; expect a few % line errors.
- voynichese.com/arXiv boxes are WORD-level only, coarse (heavily overlapping, ~10-20 px jitter on a 636x900 image). Not usable as line or glyph ground truth. Useful only as a weak cross-check (transcription alignment: each box has a token id -> word string) and for line grouping by y-clustering if desired.
- No source gives glyph boxes. Glyph level would need CTC/line-level training instead of boxes.
- Segment from Yale IIIF (not archive.org) at ~1800-2688 px wide.

## Image sources
- Yale manifest (IIIF Presentation 3): https://collections.library.yale.edu/manifests/2002046 (alt oid form: .../manifests/oid/2002046/...). 213 canvases incl. covers; canvas label = folio ("103r").
- Image URL (IIIF Image 2, level2): https://collections.library.yale.edu/iiif/2/<id>/full/<size>/0/default.jpg, e.g. 1800, wide: .../full/1800,/0/default.jpg. Ids: f1v 1006077, f2r 1006078, f68r 1006196, f78r 1006214, f103r 1006254, f108v 1006265.
- Max resolution: full size ~2650-2800 x ~3700-3800 per page (f103r 2688x3805); f68r foldout 7993x3828. Tiled, no auth. Rights field not in manifest (only provider); item is public domain per IA/Beinecke.
- Internet Archive voynich_MS_408: PDF 127 MB, JP2 zip 108 MB (single-page processed), EPUB, hOCR/DjVu (OCR of non-Latin text, junk), scandata. Public Domain Mark 1.0. Lower res than Yale IIIF (JP2 zip 108 MB / ~230 pp is much smaller); per-page dimensions not checked.
- Used 1800 px wide (4000 for f68r) in s4-data/.

## Box sources
| What | Granularity | Coverage | License |
|---|---|---|---|
| voynichese.com `https://voynichese.com/2/data/folio/script/<folio>.js` (JSON array: [0]=word list [token,count,folios,[examples]], [1]=boxes [word_id,x,y,w,h]) | word | all folios (223 files in arXiv bundle, e.g. f102r1, f67r2 sub-folios) | None stated on site; GitHub voynichese/voynichese repo license: null. Treat as unlicensed |
| arXiv 2608.17096 ancillary `anc/data/voynich-units/morphometry_voynichese/voynichese_boxes/*.js` | word, byte-identical to the site data (f103r checked: same 20614 B) | same 223 files | Code MIT (github.com/lrozanova/voynich-units); third-party data keep source terms; arXiv paper license: nonexclusive-distrib 1.0. Boxes thus inherit voynichese.com's unclear terms |
| arXiv `measure_direct_pixels.py` + results csv | ink-gap per word boundary (paper's blind audit) | sampled boundaries only; Beinecke scans not redistributed | MIT code |
- Coordinate frame: voynichese.com low-res image https://voynichese.com/2/data/folio/image/glance/color/large/<folio>.jpg (636x900 for f103r; box extents fit within it). Rescale to Yale images by ratio; pages differ in crop/rotation so need per-page alignment.
- Quality: overlay (s4-out/vc_f103r_boxes.png) shows boxes offset/overlapping, several not tight on words. Fine as hints, not as truth.
- No download/terms page found; voynichese.com home page lists folios only. No glyph boxes anywhere.

## blla results (kraken 7.1.1, `segment -bl`, default model; overlays s4-out/<folio>_ov.png)
| Page | Lines found | Visible text lines (approx) | Notes |
|---|---|---|---|
| f103r (recipes) | 74 | ~62 text + star labels | Lines follow text well, long lines OK. Extra lines = ~12 left-margin star/label boxes and stain/page-number. A few lines doubled/overlapping in dense blocks |
| f108v (recipes) | 74 | ~66 + labels | Similar; good. Few partial/short fragment lines near paragraph ends; ~8 false lines on left margin stars |
| f78r (balneo) | 57 | ~55 + labels | Text column good; lines not broken by nymph drawings (text sits beside). Labels/pipe labels picked up as lines, plausible. Few mild merges |
| f2r (herbal) | 31 | ~30 | Good on short split-column blocks; some very short fragments; small misc at corner |
| f1v (herbal) | 39 | ~35 (faint, partly lost) | Weakest: left-hand lines of faint ink partly missed, ragged/short lines, some boxes bleed over adjacent lines, false hits on root hatching (3 at bottom) |
| f68r (astro foldout) | 82 | few straight lines + many star labels + circular ring text | Straight text and labels caught; ring text on circle path NOT followed (blla gives mostly gaps on the right circle); labels boxed mostly OK. Needs separate handling |
- Not measured: precision/recall against ground truth (no GT); counts were judged visually from 1000-1400 px overlays. Console warning for f68r about invalid multi-part geometry.

## Unverified
- Whether voynichese.com data/image sources have explicit terms (no page found) - ask owner or avoid redistribution.
- Page-level resolution of IA JP2s.
- Rights wording on Yale record (manifest has none; public domain claim only seen on IA metadata).
- Exact line truth counts; line IoU. GPU/fine-tuned blla not tried (fine-tune on ~20 corrected pages is the likely next step).
- Whether all 213 canvases share the 2.6k-wide size.
