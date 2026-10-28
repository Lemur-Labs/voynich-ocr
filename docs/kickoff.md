# Voynich OCR — Kickoff

Oct 26, 2026 · @Brian

## Charter

The bet: an agent-driven workflow ships a public research repo with a scored result and a community-reviewed writeup by 2026-11-23, using under four owner hours in total. Voynich is the test case for the workflow. It is low-stakes and fully public, and it has an outside community (voynich.ninja, Zandbergen) that will review the work for free.

**Deliverables**

1. **Disagreement map.** Per glyph and per page, where the five main transliterations (ZL, Takahashi, Currier, GC, FSG) disagree. This is the label-noise floor. Zandbergen's 2022 keynote compared these files at the transliteration level; what's new is mapping the disagreement per glyph and tying it to the images.
2. **Glyph clustering against the map.** Clusters built from image features alone, scored on whether they explain where transcribers disagree.
3. **Recognizer as an instrument.** Its per-glyph confidence must be calibrated against the map: low confidence where transcribers disagree. That replaces the old CER-against-ZL test, which only measured agreement with Zandbergen.
4. **Known-answer arm.** Naibbe-cipher text rendered in a synthetic hand built from the clustered glyphs, so accuracy can be measured where the answer is known. This bounds performance on synthetic ink; it doesn't measure it on the manuscript.
5. **Public repo and writeup**, posted to voynich.ninja for review.

**Non-goals**

- Deciphering or translating the text.
- Direct revenue. The buyer test below is about reuse, not sales.
- Hand-labeling glyphs.
- Owner-run training loops.

**Time box:** four weekends of agent time and four owner hours in total. GPU work runs on a GCP VM, never on owner time.

**Kill criteria** (any one ends it):

- Owner hours go above four.
- No scored claim by 2026-11-23.
- Calibration is no better than chance against the disagreement map. Concretely: per-glyph confidence predicts transcriber disagreement with an AUROC whose bootstrap 95% interval stays above 0.5.
- No outside reviewer engages with the writeup.

**Buyer test.** Calibrated transcription of unknown or contested scripts has an audience that pays in grants: digital-humanities labs, archives with undeciphered or damaged holdings, and their funders (NEH, Horizon Europe cultural-heritage calls). Threshold: ten contacts, three replies, one named lab that would cite or reuse the disagreement-map method.

As first written it needed 30 to 40 owner hours against a budget of two a week. Reframed, it is a public, reviewed proof that an agent-driven workflow can run a research project unattended.

## Background

The manuscript is still undeciphered as of October 2026. No AI or human claim has been verified by experts, despite a steady stream of "solved it" posts on Zenodo and the forums.

**Agreed**

- Genuine 15th-century object: the vellum radiocarbon-dates to 1404–1438. That rules out a Voynich forgery and Roger Bacon.
- European, probably northern Italy or the Alpine region. Exact origin still debated.
- Sections: herbal, astronomical/zodiac, balneological, cosmological, pharmaceutical, recipes.
- Several hands. Currier found two statistical "languages" (A and B); Davis (2020) identified five scribes.
- The text has real structure: Zipf-like word frequencies, but rigid word shapes, low entropy and frequent repeated words.

**Not agreed**

- What the text is: a cipher, a natural language in an invented script, a constructed language, or systematic meaningless text.
- What the plants depict, who made it, and why.

**Recent work that matters to this project**

- *Naibbe cipher* (Greshko, Cryptologia, Nov 2025): a dice-and-cards substitution cipher that turns Latin or Italian into Voynich-like text. Not a solution, but it gives us synthetic text with a known answer.
- *Multispectral imaging* (Davis, 2024): 10 pages imaged in 2014, released publicly. Revealed early owners' marginal alphabets; no decryption key.

**Why OCR matters here:** every statistical attack runs on a human transliteration, and transcribers disagree on where one glyph ends and the next begins. Zandbergen noted in 2022 that an unknown alphabet plus overlapping lines made automatic transcription insurmountable. Line-level, segmentation-free recognizers have improved a lot since, which is the opening.

## Data sources

Everything needed is free. The images are public domain; the transliterations are free to use with attribution to their authors.

| Source | What it gives us | Role |
| --- | --- | --- |
| [Yale Beinecke digital library, MS 408](https://beinecke.library.yale.edu/collections/highlights/voynich-manuscript) (catalog 2002046) | Full-resolution scans of every page, with a download-all option and IIIF access | Primary images |
| [Internet Archive mirror](https://archive.org/details/voynich_MS_408/mode/2up) | The Beinecke scans in one 335 MB bundle, public domain | Fallback images |
| [ZL transliteration](https://www.voynich.nu/data/ZL_ivtff_2b.txt) (Zandbergen–Landini) | Complete EVA text keyed by folio and line; includes uncertain readings | Training labels |
| Takahashi (IT), RF, Currier, FSG, GC files at [voynich.nu/data](https://www.voynich.nu/data/) | Independent transliterations | Disagreement map, cross-check |
| [IVTFF format spec](https://mail.voynich.nu/software/ivtt/IVTFF_format.pdf) and [ivtff on PyPI](https://pypi.org/project/ivtff) | The file format and a Python parser | Parsing |
| Multispectral images, *Manuscript Road Trip* (Davis, Sept 2024) | UV/IR images of 10 pages | Optional: faded strokes |
| Naibbe cipher ([Cryptologia, 2025](https://doi.org/10.1080/01611194.2025.2566408)) | A way to generate Voynich-like text from known Latin | Synthetic controls |

The ZL file uses special `&nnn;` symbols and `[a:b]` alternative readings. Training v1 drops lines with alternatives; v2 uses them as soft labels.

## Architecture

No result is scored against ZL alone. Each output is checked against either the disagreement map or text whose answer is known, which is what breaks the circularity of training and testing on the same transliteration.

&#91;embedded content: pipeline · 3 scored outputs\]

Stack: Python, Kraken for line segmentation (and possibly recognition), PyTorch for clustering features, the ivtff parser for labels. One repo, one `make dataset` target that rebuilds everything from the snapshot.

## Phases, gates and kill criteria

One phase per weekend, with owner hours checked at every gate. Each gate either passes, narrows the scope, or ends the project early.

&#91;embedded content: roadmap · 4 weekends, 3 gates, kill date\]

The disagreement map comes first because it needs no images, no segmentation and no GPU, so Gate 0 is cheap to pass or fail. Whatever happens, what's finished gets published, so even a killed bet leaves the map behind.

## Risks and open questions

The biggest risk is owner hours creeping past four; the second is scope creep into decipherment.

| Risk | Effect | Mitigation |
| --- | --- | --- |
| Owner gets pulled into debugging or reviewing | The four-hour budget is gone in week 1 | Owner hours logged at every gate; the agent escalates only at gates |
| Drift into "let's just try to decipher it" | The time box disappears | Decipherment stays a non-goal; the Naibbe arm is the only cipher work in scope |
| Transliterations use different alphabets | The disagreement map compares unlike symbols | Convert all five files to Zandbergen's STA unified alphabet before comparing |
| Calibration test still rests on human labels | A weaker claim than true ground truth | Report it as agreement-with-disagreement; the Naibbe arm is the true-ground-truth check |
| Synthetic hand is too clean | Known-answer accuracy overstates real performance | Present it as a ceiling, not an estimate |
| Line segmentation fails where lines overlap or wrap around drawings | Bad crops and misaligned labels | Start with text-only pages (recipes section) |
| No lab replies to the buyer test | No evidence the method gets reused | Drop the buyer test; the workflow claim still stands on its own |
| Yale or voynich.nu access changes | Pipeline breaks | Snapshot images and transliteration files on day one |

**Open questions**

- [ ] Which recognizer: Kraken (simplest pipeline), PyLaia, or a fine-tuned TrOCR?
- [ ] Output alphabet: EVA, STA, or a lower stroke level that makes fewer assumptions?
- [ ] Which ten contacts for the buyer test, and who sends them?
- [ ] Who in the voynich.ninja community to invite as first reviewer?

## Sources

- [Beinecke Library: the Voynich Manuscript](https://beinecke.library.yale.edu/collections/highlights/voynich-manuscript)
- [Internet Archive: Voynich MS 408](https://archive.org/details/voynich_MS_408/mode/2up)
- [ivtff on PyPI](https://pypi.org/project/ivtff)
- [IVTFF format spec, Zandbergen](https://mail.voynich.nu/software/ivtt/IVTFF_format.pdf)
- [Zandbergen: transliteration material, 2022 conference](https://voynich.nu/extra/conf2022_extra.html)
- [Voynich Ninja: automatic transcription thread](https://www.voynich.ninja/printthread.php?tid=3742)
- [Greshko, Naibbe cipher coverage, Sci.News](https://www.sci.news/othersciences/linguistics/voynich-manuscript-cipher-14466.html)
- [Language Log: multispectral imaging](https://languagelog.ldc.upenn.edu/nll/?p=65930)
- [Decipherment of Historical Manuscript Images (arXiv 1810.04297)](https://arxiv.org/pdf/1810.04297)
- [Historical Document Processing survey (arXiv 2002.06300)](https://arxiv.org/pdf/2002.06300)
- [Symbol recognition study on the Voynich manuscript (CEUR-WS)](https://ceur-ws.org/Vol-3643/paper10.pdf)
- [Voynich status 2026, YourStory](https://yourstory.com/2026/03/voynich-manuscript-unsolved-mystery)
