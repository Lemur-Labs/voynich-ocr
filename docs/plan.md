# Voynich OCR — Plan

Oct 26, 2026 · proxy draft for @Brian · amends [kickoff.md](kickoff.md) where marked **[K-n]** · decisions in force: [decisions.yaml](decisions.yaml)

## 0. Process frame (why this shape)

Three proven pieces, each doing a job the others don't:

| Piece | Source | Job here |
|---|---|---|
| Tailored R&T lifecycle with Key Decision Points | NASA NPR 7120.8 (R&T projects; tailoring is expected), SE engine from NPR 7123.1 / SP-2016-6105 | Phases, gates, and the rule that a gate can only pass, narrow, or kill |
| Trade studies: must-criteria filter → weighted Pugh vs a datum → decision record with reversal cost | NPR 7123.1 Decision Analysis process | Every stack/design decision lands as a row in `docs/decisions.yaml` (`VO-` prefix), citing its trade study |
| Pre-registered analysis plan, frozen and hashed before data is scored | Registered-reports practice (psych/ML eval) | Makes "automated decisions" legitimate: the rule is fixed before the evidence, so an agent applying it isn't choosing |

Inside each phase the loop is CRISP-ML(Q)-style build → measure → learn, with the eval harness built first (scorers exist before models). The NASA mapping, compressed:

| NASA (7120.8, tailored) | This project | Dates |
|---|---|---|
| Pre-Phase A / MCR | Kickoff (done) + this roadmap | Oct 26 |
| Formulation / KDP-A (SRR+PDR collapsed) | **F0**: gap closure, spikes, Pugh, pre-registration, snapshot, harness | Oct 26–30 |
| Implementation, one TRR per increment | **W1–W4**, one build/test/learn increment per weekend | Oct 31 – Nov 22 |
| KDP per increment | **G1–G3** (pass / narrow / kill) | Nov 2, 9, 16 |
| Closeout / decommission | **G4** release + review + lessons-learned | Nov 23 |

What I deliberately dropped from NASA: CDR as a separate review, configuration control boards, independent V&V org, formal risk scoring matrices. At this scale they cost more owner hours than the risks they retire. The red-team agent (§6) stands in for IV&V.

## 1. Kickoff corrections from research

Fix these before anything is built. Each is a fact I checked, not an opinion.

| # | Kickoff says | Actually | Consequence |
|---|---|---|---|
| K-1 | ZL at `ZL_ivtff_2b.txt` | Current file is `ZL3b-n.txt` (2025-06-04) | Stale link; snapshot the current set |
| K-2 | Five transliterations: ZL, Takahashi, Currier, GC, FSG | Files: `ZL3b-n`, `IT2a-n` (Takahashi), `CD2a-n` (Currier–D'Imperio, 130 KB), `GC2a-n` (v101), `FG2a-n` (FSG, 259 KB). `VT0e-n` is Takahashi again; `RF1b-*` is an automatic ZL+GC merge | Exclude VT and RF from the count. **Currier and FSG are partial, with coarser alphabets.** Most text gets 3 independent readings, not 5. The map has to report coverage per locus, and "noise floor" has to be stated per coverage tier |
| K-3 | Use `ivtff` from PyPI | v0.0.1, a single release from Feb 2023, one author; the docs don't say whether it handles `&nnn;` or `[a:b]` | Don't depend on it. See D5 |
| K-4 | Output alphabet open: EVA / STA / stroke level | STA exists (v1.03, Sept 2025; header code `IS16`, a superset of FSG/Currier/EVA/v101). **STA-AAA**, Zandbergen's analytical stroke-family alphabet, also exists | The stroke-level option is already defined, so no invented alphabet is needed. See D2 |
| K-5 | Kill: "AUROC whose bootstrap 95% CI stays above 0.5" | Written as the pass condition but listed under kill. AUROC also measures *discrimination*, not *calibration* | Restate (§3). Add a calibration metric (ECE / reliability curve). Bootstrap **by page**, not by glyph, because glyphs on a page aren't independent |
| K-6 | No result scored against ZL alone, so circularity is broken | Two leaks remain. (a) The recognizer is trained on ZL, and ZL is one of the map's voters. (b) Glyph crop boundaries for clustering come from a ZL-trained CTC alignment, so the "image features alone" clusters inherit ZL's segmentation | (a) Add a **leave-ZL-out map** as a robustness score. (b) Add a label-free crop proposer (connected components / stroke skeleton) as a control arm |
| K-7 | Post the writeup at the end | A forum post on Nov 22 leaves ~1 day for the "reviewer engages" kill criterion | **Post the map after G1 (Nov 2).** That starts the review clock 3 weeks earlier and still honors "whatever's finished gets published" |
| K-8 | Naibbe "gives us synthetic text" | The reference implementation is **Excel workbooks on Zenodo**, plus 20 reference ciphertexts (forum-gated Dropbox). No code repo | Port to Python. The 20 reference ciphertexts serve as the port's known-answer test |
| K-9 | "What's new is per-glyph mapping" | Novelty holds. Closest 2026 work: Rozanova & Temerev, arXiv 2608.17096 (Aug 2026), does pixel morphometry with per-folio bounding boxes, but on ZL only, and its uncertainty analysis covers blanks, not glyphs | Cite it. Check whether their `voynichese_boxes` can stand in for segmentation (D4) |
| K-10 | Kraken | Current release is 7.1.1 (Sept 2026) | Pin it |
| K-11 | "Four weekends of agent time" | Standalone repo (VO-001, VO-002). F0 runs on weekdays this week | Agent time on weekdays costs no owner hours (R2). The claim is that an agent-driven pattern can run research unattended, and the pattern is what gets reused |

## 2. Roadmap

```
Oct 26─────30 | 31─Nov1 |2| 7──8 |9| 14─15 |16| 21──22 |23
F0 Formulation| W1 Map  |G1| W2 Seg+Clust |G2| W3 Recog+Calib |G3| W4 Naibbe+Release |G4
 spikes·Pugh  | no GPU  |post| GPU light |  | GPU            |  | GPU light           | kill/ship
 prereg·harness            map v0
```

### F0 — Formulation (Oct 26–30, no GPU)
| Step | Output | Done when |
|---|---|---|
| F0.1 Snapshot | Images (IA bundle + IIIF manifest) and all `voynich.nu/data` files, including `sta/` and STA1_def.pdf, written to GCS. Git holds the fetch script and a SHA-256 manifest, not the third-party files (R7) | `make snapshot-verify` is green |
| F0.2 Spikes S1–S6 (§4) | One evidence note per spike, ≤1 page each | Every "?" cell in the Pugh tables is resolved |
| F0.3 Pugh re-score → decisions | DEC records with alternatives and reversal cost | The auto-decide rule (§5) applied; escalations batched to KDP-F |
| F0.4 Pre-registration | `prereg.md`: hypotheses, metrics, thresholds, bootstrap scheme, decision rules per gate. Hashed and committed | The hash appears in the KDP-F packet. Later edits are amendments, logged with a reason |
| F0.5 Eval harness | Scorers for all three outputs, tested on synthetic data with known injected disagreement | Each scorer recovers an injected effect and returns null on a shuffled control (non-vacuity) |
| **KDP-F** (owner, 30 min) | Approve prereg + escalated decisions | |

### W1 — Disagreement map (Oct 31 – Nov 1, no GPU, no images)
- **Build:** parse 5 files → STA → per-locus alignment (IVTFF locus ids line up across files; within a line, edit-distance alignment in STA) → per-glyph disagreement, per-page rate, per-pair confusion matrices, coverage tier per locus, leave-one-out maps.
- **Test:** differential test of the parser against Zandbergen's `ivtt` output; injected-perturbation recovery; spot-check 20 loci against images by agent screenshot. No owner involvement.
- **Learn:** which pairs disagree, on what, and where in the manuscript (section, Currier A/B, Davis scribe).
- **G1 (Nov 2):** pass → **post map v0 to voynich.ninja** and start the reviewer outreach. Narrow → drop the partial sources and ship a 3-way map. Kill → impossible here unless the data is broken.

### W2 — Segmentation + glyph clustering (Nov 7–8)
- **Build:** line segmentation (D4) on the text-heavy sections first. **Train the first Kraken model here.** CTC alignment needs one, so it can't wait for W3. Glyph crops come from two proposers: (a) CTC alignment and (b) a label-free proposer (K-6). Feature embeddings (D3), then clustering.
- **Test:** the pre-registered cluster score. Do high-disagreement loci fall in clusters with higher label entropy across transcribers (AMI / entropy gap vs a shuffled baseline, page bootstrap)?
- **G2 (Nov 9):** pass / narrow (fewer sections, one proposer) / kill clustering. If clustering is killed, deliverable 4 needs a different glyph source, so G2 also decides the Naibbe hand's source.

### W3 — Recognizer + calibration (Nov 14–15) — the main scored claim
- **Build:** retrain or keep the W2 Kraken model (D1; same pages, same seed). Per-glyph confidences come from the full CTC posteriors, with temperature scaling on the validation pages (`docs/prereg.md` H3).
- **Test (pre-registered):** AUROC of (1 − confidence) predicting disagreement; page-clustered bootstrap CI; ECE; the same on the leave-ZL-out map. Splits are by page and stratified by section/hand.
- **G3 (Nov 16):** pass if the CI lower bound is > 0.5 on both the full and leave-ZL-out maps. Narrow if only the full map passes: report it with the caveat. Kill if neither passes. Even on a kill, the map and clusters ship.
- **In parallel, weekdays Nov 9–13:** port Naibbe and validate it on the 20 reference ciphertexts.

### W4 — Known-answer arm + release (Nov 21–22)
- **Build:** Naibbe text → synthetic hand (D7) from G2 clusters → recognizer → CER on known text. Reported as a ceiling.
- **Release:** repo with `make dataset` and `make all`, Zenodo DOI, writeup, red-team pass (§6), forum post v1 (an update to the G1 thread, not a new cold post).
- **G4 (Nov 23):** score against the kill criteria, record owner hours, write lessons-learned for the research-bet template (R5).

### Re-planning triggers (any one forces an out-of-cycle replan, batched to the next gate unless budget-critical)
- A spike falsifies an assumption a later phase depends on (e.g. S4 shows Kraken segmentation fails on most pages).
- A phase misses its "done when" by Sunday 18:00 → narrow, never extend.
- GCP spend > 150% of estimate, or owner hours projected > 3.5.
- A reviewer raises a methodological objection: triage within 48h and amend the prereg publicly if it's valid.

## 3. Restated scored claims and kill criteria (for the prereg)

| Claim | Metric | Pass | Kill |
|---|---|---|---|
| Map | Coverage-tiered per-glyph disagreement; reproducible from snapshot | `make map` is deterministic (byte-identical twice) | Data unparseable |
| Clusters explain disagreement | Entropy gap vs shuffled-label null, page bootstrap 95% CI | CI excludes 0 | CI includes 0 → drop the claim, keep the clusters as data |
| Recognizer is an instrument | AUROC(1−conf → disagree), page bootstrap, B=2000, seed pinned; ECE after temperature scaling | AUROC CI lower bound > 0.5 on full **and** leave-ZL-out maps | CI includes 0.5 on both |
| Known-answer ceiling | CER on Naibbe synthetic | Reported. No threshold, since it's a bound | — |
| Engagement | ≥1 substantive outside reply | By Nov 23 | None |
| Owner hours | Logged at every gate | ≤4 | >4 |

## 4. Research spikes (F0, parallel)

| Spike | Question | Resolves |
|---|---|---|
| S1 | Does a deterministic ZL→STA→STA-AAA mapping exist (STA1_def, `sta/`)? Can CD/FG/GC/IT all be lifted to STA without loss? | D2, W1 feasibility |
| S2 | `ivtt` availability, build, and conversion coverage; parser edge cases (`&nnn;`, `[a:b]`, `{}` comments, locus types) | D5 |
| S3 | Kraken 7.1.1: per-character confidence and alignment API; training on a novel charset; GPU-hours for ~5k lines | D1, cost |
| S4 | Kraken default `blla` segmentation quality on 10 sample pages across sections; licensing and coverage of voynichese.com / Rozanova–Temerev boxes | D4 |
| S5 | DINOv3 license terms for a public repo; DINOv2 fallback | D3 |
| S6 | Naibbe Zenodo record: license, workbook logic, reference ciphertexts reachable without forum login | W4 feasibility |

## 5. Trade studies (prior scores; re-scored after spikes)

**How to read these:** must-criteria filter options out first. Then each option is scored against the **datum** (first row) at −1/0/+1 per criterion, multiplied by the weight, and summed.

**Auto-decide rule** (replaces owner judgment for the routine cases): the agent decides and logs a DEC record when the leader's margin is ≥15% of the weight sum, **and** no must-criterion or leading-score cell is unverified, **and** reversal cost is low. Otherwise the decision is batched to the next gate as an escalation with a recommendation attached. It never interrupts the owner mid-phase.

### D1 — Recognizer · must: emits per-glyph confidence; open-source; runs unattended
Weights: confidence quality/calibratability 5 · glyph→image alignment 4 · data efficiency 4 · unattended operability 4 · reuse by DH labs (eScriptorium) 3 · GPU cost 2 · accuracy ceiling 2 (Σ24)

| Option | conf | align | data | ops | DH | cost | ceil | Σ |
|---|---|---|---|---|---|---|---|---|
| **Kraken CTC (datum)** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** |
| PyLaia | 0 | 0 | 0 | −1 | 0 | 0 | 0 | −4 |
| TrOCR fine-tune | −1 | −1 | −1 | 0 | −1 | −1 | +1 | −16 |
| VLM fine-tune (Qwen-VL / CHURRO-class) | −1 | −1 | −1 | −1 | −1 | −1 | +1 | −20 |

→ **Kraken. Auto-decided** (margin 17%). Rationale that matters: autoregressive decoders cascade errors and are overconfident, which is fatal when confidence *is* the instrument. 2026 low-resource evidence (Coptic SCAM dataset) favors pure CTC. Kraken/eScriptorium is also what the buyer-test labs already run, so the method ports straight to them. Reversal cost: low (the dataset is reusable).

### D2 — Recognizer output alphabet · must: maps deterministically into the map's STA units
The map itself is in STA. That's a constraint (K-4), not a trade.
Weights: alignment to map units 5 · fewest segmentation assumptions 4 · label availability 4 · class count vs data 3 · reviewer legibility 3 (Σ19)

| Option | align | seg | labels | classes | legible | Σ |
|---|---|---|---|---|---|---|
| **EVA basic (datum)** | 0 | 0 | 0 | 0 | 0 | **0** |
| STA (~235 symbols in ZL alone) | +1 | 0 | 0 | −1 | 0 | +2 |
| STA-AAA (stroke families) | +1 | +1 | −1 | +1 | −1 | **+5** |

→ **Escalate.** STA-AAA leads (margin 16%), but its must-criterion depends on S1. It's also the most interesting answer scientifically: strokes are where transcribers actually split and merge glyphs. My recommendation: STA-AAA if S1 confirms the mapping, EVA basic for v1 otherwise. Proposed as a pre-registered rule instead of an owner call (R3).

### D3 — Clustering features · must: no label-derived signal (excludes recognizer embeddings)
Weights: captures stroke-shape distinctions 4 · reproducibility 3 · operability 3 · compute 2 (Σ12)

| Option | shape | repro | ops | compute | Σ |
|---|---|---|---|---|---|
| **HOG / handcrafted (datum)** | 0 | 0 | 0 | 0 | **0** |
| DINOv3 frozen embeddings | +1 | 0 | 0 | −1 | **+2** |
| Self-trained contrastive | +1 | −1 | −1 | −1 | −4 |

→ **DINOv3, conditional on S5** (license). HOG is kept as the control arm, not discarded. Auto-decides once S5 clears.

### D4 — Line segmentation · must: no hand-labeling (charter non-goal)
Weights: hand labor 5 · coverage 3 · overlap accuracy 3 · licensing clarity 3 (Σ14)

| Option | labor | cover | overlap | license | Σ |
|---|---|---|---|---|---|
| **Kraken `blla` default (datum)** | 0 | 0 | 0 | 0 | **0** |
| `blla` fine-tuned on corrected pages | −1 | 0 | +1 | 0 | −2 (and fails the must: correction is hand-labeling) |
| Reuse published boxes (voynichese.com / arXiv 2608.17096) | 0 | +1 | +1 | −1 | **+3** |
| Datum restricted to text-heavy sections | 0 | −1 | +1 | 0 | 0 |

→ **Escalate only if S4 is ambiguous.** Default: datum plus a section restriction, with boxes adopted if S4 clears licensing.

### D5 — IVTFF parsing
Weights: correctness on `&nnn;`/`[a:b]` 5 · maintenance risk 3 · testability 3 · effort 2 (Σ13)

| Option | correct | maint | test | effort | Σ |
|---|---|---|---|---|---|
| **`ivtff` PyPI 0.0.1 (datum)** | 0 | 0 | 0 | 0 | 0 |
| Own parser, ~200 LOC | +1 | +1 | +1 | −1 | **+9** |
| Zandbergen's `ivtt` via subprocess | +1 | 0 | 0 | 0 | +5 |

→ **Own parser, with `ivtt` as the differential test oracle. Auto-decided.**

### D6 — Experiment tracking
Weights: owner attention 5 · reproducibility 4 · public reproducibility for reviewers 4 · setup 3 (Σ16)

| Option | attn | repro | public | setup | Σ |
|---|---|---|---|---|---|
| **Make + content-addressed artifacts + JSON metrics in git; Zenodo at release (datum)** | 0 | 0 | 0 | 0 | **0** |
| DVC | 0 | 0 | 0 | −1 | −3 |
| W&B | 0 | 0 | −1 | 0 | −4 |
| MLflow | 0 | 0 | −1 | −1 | −7 |

→ **Datum. Auto-decided.** Reviewers need `make all` and a DOI, not a dashboard.

### D7 — Synthetic hand
Weights: schedule risk 5 · confound control 4 · cost 3 · realism 3 (Σ15)

| Option | sched | confound | cost | real | Σ |
|---|---|---|---|---|---|
| **Glyph-collage from cluster exemplars + jitter (datum)** | 0 | 0 | 0 | 0 | **0** |
| Generative handwriting model | −1 | 0 | −1 | +1 | −5 |

→ **Collage. Auto-decided.** It's reported as a ceiling anyway (charter).

### Re-scored after spikes (F0.3, 2026-10-27)

Evidence is in `docs/spikes/`. Each outcome is a `VO-` row.

| Decision | Outcome | What changed | Row |
|---|---|---|---|
| D1 recognizer | **Kraken 7.1.1 CTC, auto-decided** | S3: full per-frame posteriors are available (`return_logits=True`). The built-in `confidences` is a peaky max and isn't used. Requires Python 3.12; Apache-2.0 | VO-011 |
| D2 output alphabet | **STA-AAA** | S1: deterministic mappings exist and every source is already published in STA. Decided by the VO-005 rule | VO-010 |
| D3 cluster features | **DINOv2 ViT-S/14, auto-decided; HOG control** | S5: DINOv3 is gated and carries pass-through license terms, which costs reviewer reproducibility (repro −1 → Σ −1). DINOv2 is Apache-2.0 (LICENSE checked) and the same size (Σ +2) | VO-012 |
| D4 segmentation | **Kraken default `blla` + post-filter, auto-decided** | S4 and my own check of the f103r overlay: text lines are traced; false lines on stars, margins and page numbers. Published boxes are word-level, loose, and of unclear license, so they score −1 on license and +0 on accuracy → Σ 0. Pages whose filtered line count ≠ their locus count are excluded rather than corrected (no hand-labeling) | VO-013 |
| D5 parser | **Own parser, auto-decided; `ivtt` as local oracle only** | S2: `ivtt` has no license, so it's fetched and run but never vendored. The format is `@nnn;`, not `&nnn;`. `ivtt` drops `!`-locator loci | VO-014 |
| D6, D7 | unchanged, auto-decided | — | VO-015 |
| Naibbe arm | **Vendor Greshko's own Python** | S6: github.com/greshko/naibbe-cipher (MIT, citation requested) plus the full tables on Zenodo (CC BY 4.0). The 20 reference ciphertexts weren't reachable; the known-answer test uses the shipped ciphertext/plaintext pairs and round-trips instead | VO-016 |

Coverage, correcting K-2 (S2): ZL 227 pages, GC 226, IT 225, FG 202, CD 131. All five cover 131 pages (2,185 loci), and those are herbal and balneological only. Test pages therefore come from the 202 pages with ≥4 sources (`docs/prereg/splits.json`).

### Cost estimate (to verify in S3)
GCP g2 (L4) **spot** instances for W2–W4 training/inference, at most a few tens of GPU-hours. **Budget alert at $100, hard stop at $200.** Storage for the snapshot is negligible. The dominant cost is agent tokens, not compute, which is why §6 is mostly about *not* spawning things.

## 6. Proposed workflows and agents (cost vs long-term savings)

| # | Proposal | Model / effort | When | Cost | Saves / buys | Verdict |
|---|---|---|---|---|---|---|
| A | **Spike researchers** S1–S6, one fresh agent each, terse evidence note | Sonnet, lower effort, parallel | F0 once | 6 short runs | Turns every "?" in §5 into evidence; it's what makes auto-decide safe | **Do** |
| B | **Pre-registration + hash lock.** A procedure, not an agent | none | F0 | ~1h of agent time | Credibility with voynich.ninja (the community is saturated with "solved it" posts); legitimizes automated gate decisions | **Do. Highest ROI item here** |
| C | **Red-team reviewer**, a fresh Opus agent handed only the claim and artifacts (not our reasoning), told to act as a hostile domain reviewer: circularity, overclaiming, stats | Opus | Each gate + pre-post | 4–5 runs | Directly targets kill criterion #4 and the reputational downside. Catches K-5/K-6-class errors before outsiders do | **Do** |
| D | **Gate packet**: a deterministic script compiles metrics + prereg pass/fail + hours + escalations into one page, with Sonnet adding ≤5 lines of narrative | script + Sonnet | Each gate | trivial | Keeps owner review ≤15 min per gate. This is what protects the 4h budget | **Do** |
| E | **VM experiment runner**: scripted sweep with a budget cap; applies the pre-registered decision rule in code; the agent reads results only | code | W2–W4 | none beyond compute | Unattended training without an agent babysitting the GPU (owner-run loops are a non-goal) | **Do** |
| F | **Outreach drafter**: researches 10 buyer-test contacts and 3–5 reviewer candidates; drafts personalized messages | Sonnet | after G1 | 1–2 runs | The buyer test without owner research time. Seed list: DECODE / Megyesi (Uppsala, cipher transcription), eScriptorium/Kraken team (EPHE/PSL), Zandbergen, Davis, Greshko, Rozanova–Temerev | **Do; you send (R4)** |
| G | **Research-bet template**: encode F0 → prereg → Pugh/auto-decide → gated increments → red-team → closeout as a template (docs skeleton + issue types + agent prompts) | Opus once | After G4, from lessons-learned | one build | Every future research bet starts at F0 instead of a blank kickoff. This is the long-term saving | **Propose. New abstraction, so it needs your say-so (R5)** |
| ✗ | Long-lived multi-agent swarm; LLM-as-judge for metrics; Workflow fan-out per decision; standing up MLOps (MLflow/W&B) | — | — | high | Code scores metrics, scripts route, fresh per-task agents | **Don't** |

### Owner-hour budget (4.0h)
| KDP-F | G1 + forum post | G2 | G3 | G4 + release sign-off | Outreach sends | Reserve |
|---|---|---|---|---|---|---|
| 0.5 | 0.5 | 0.25 | 0.25 | 0.75 | 0.75 | **1.0** |

Each phase launch (a one-line "run W1 per docs/plan.md" to a fresh Claude Code session) is ~2 min and goes in the hours log. Five launches ≈ 10 min, taken from the reserve.

## 8. Recommendations on the open decisions

Each becomes a `VO-` row once you say yes.

| # | Decision | Recommendation | Why |
|---|---|---|---|
| R1 | Who drives | One fresh Claude Code session per phase, launched by you with one line. The agent opens PRs; CI + the red-team check gate them; the agent merges on green. You review at gates only | The cheapest unattended-enough driver. Scheduled cloud routines would save the ~10 min of launches but cost more to set up than they save over 5 launches |
| R2 | F0 on weekdays | Yes | "Four weekends" bounds compute and your calendar. Agent weekday time costs no owner hours, and skipping F0 means W1 starts without a pre-registration |
| R3 | Output alphabet (D2) | Taken off your plate: pre-register the rule "STA-AAA if S1 shows a deterministic mapping from all five sources, else EVA basic" | It's an evidence question, not a preference. The rule is fixed before S1 reports |
| R4 | Who sends outreach | **You**, from your own accounts, in one 45-min batch after G1, sending agent-drafted messages. Disclose AI assistance in the post and the writeup | voynich.ninja is saturated with AI "solved it" posts. A project account, or an agent posting as you, risks the engagement kill criterion and is close to impersonation. Your name also lifts reply rates for the 3-reply threshold |
| R5 | Research-bet template (§6 G) | Yes, but build it after G4 from the lessons-learned | Building it now would encode guesses. After G4 it encodes what worked |
| R6 | Stricter criteria (K-5 restatement, leave-ZL-out) | Accept | Reviewers will run the leave-ZL-out check themselves. A narrow we report beats a takedown they post. The inverted K-5 wording has to be fixed regardless |
| R7 | Visibility and licensing | Private until G1, then public with the map post. Code MIT, writeup and map CC BY 4.0. Third-party transliterations and images are fetched by script with hash checks, never committed | The charter requires a public repo. The transliterations are free to use with attribution, but that isn't a license to redistribute them |

## Sources
- [voynich.nu/data](https://www.voynich.nu/data/) and its [README](https://www.voynich.nu/data/000_README.txt) — file set, prefixes, coverage
- [STA overview](https://voynich.nu/extra/sta.html), [STA1 definition](https://mail.voynich.nu/data/sta/STA1_def.pdf), [STA-AAA](https://voynich.nu/extra/sta-aaa.html), [Zandbergen 2022 keynote](https://ceur-ws.org/Vol-3313/keynote1.pdf)
- [ivtff on PyPI](https://pypi.org/project/ivtff/) · [Kraken on PyPI](https://pypi.org/pypi/kraken) · [kraken.re](https://kraken.re/main/)
- [Rozanova & Temerev, arXiv 2608.17096](https://arxiv.org/abs/2608.17096)
- [Naibbe thread, Voynich Ninja](https://www.voynich.ninja/printthread.php?tid=4848) · [coverage](https://letsdatascience.com/news/greshko-proposes-naibbe-cipher-replicating-voynich-patterns-17bb8816)
- [Automatic transcription thread](https://www.voynich.ninja/printthread.php?tid=3742) · [voynich.nu on transliteration](https://www.voynich.nu/extra/sp_transcr.html)
- [SCAM Coptic HTR dataset, arXiv 2606.15987](https://arxiv.org/pdf/2606.15987) · [Old Nepali HTR, arXiv 2512.17111](https://arxiv.org/pdf/2512.17111)
- [NPR 7120.8A](https://soma.larc.nasa.gov/stp/DYNAMIC/pdf_files/NPR%207120.8A%20Technology%20Management.pdf) · [7120.8 tailoring, Aerospace Corp workshop](https://aerospace.org/sites/default/files/2024-12/1350_%20Karol%20G_MA%20in%207120.8_karolg_AMA%20Workshop%20v1.pdf)
