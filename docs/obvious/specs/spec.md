# voynich-ocr: ready to publish

> Exported from the Obvious project on 2026-11-15 (blueprint artifact `voynich-ocr spec`,
> created 2026-11-13, approved by the owner the same day). Converted from the Obvious
> blueprint to Markdown; content unchanged.

*Autobuild initiative · Lemur-Labs/voynich-ocr*

Take the repo from "writeup drafted for owner review" to ready to publish: reproduce the
scored numbers that can run here, audit the writeup against its own results, and put the
disagreement map at a URL. The one decision this document asks for: approve this spec.

## Problem and decision

The pre-registered research program (G1–G4) is finished and `docs/writeup.md` is drafted
for owner review. The owner's brief asks for three things before the repo can be called
ready to publish, and each is a testable claim about work that already exists.

**Reproduction.** From a fresh sandbox, every scored number that can run on CPU must
reproduce byte-identically against `results/` — including the H1 disagreement map
(`results/map-v0/summary.json`, gated rate 0.045939) — with a CI job proving the H1 map
on every PR, and every GPU-bound number listed with its reason.

**Writeup audit.** Every figure in `docs/writeup.md` must be traced to a results file or
a decisions row, with discrepancies recorded as `VO-` rows (`by: obvious`) and
corrections proposed in a PR — never silently edited.

**Map explorer.** A static, buildless disagreement explorer at a hosted URL, generated
from the published map outputs, showing where the five transliterations disagree without
redistributing them or the Beinecke images, verified with Playwright at 1280px and 390px
with axe passing. CI green on main and a current README status finish the list.

> **The decision to approve (locked):** Approve this spec. It builds three things — the
> reproduction harness, the writeup audit, and the map explorer — as small PRs to main,
> merged when green, under the repo's own rules. It asks no owner time beyond this
> approval (~15 minutes). One question is folded into it: the G2–G4 scored numbers
> depend on fine-tuned model weights that a fresh sandbox cannot fetch, so they are
> listed as not run with reasons recorded, unless the owner chooses to expose the pinned
> weights (see *Locked decisions*).

> **Scope boundary (invariant):** Non-goals, from the brief and AGENTS.md: no
> decipherment; no edits to `docs/prereg.md`; no GPU work or cloud resources; no
> `by: brian` rows; the repo is not made more public, nobody is contacted, and
> publishing stays the owner's. Where the brief leaves a choice open, the choice is made
> here, recorded, and the work continues; after approval, decisions are raised only
> where the build must depart from this spec.

## What I read, and what it changed

All items below were read this session, on main `83b2915` (fresh clone of
Lemur-Labs/voynich-ocr, 2026-11-13).

**AGENTS.md.** The rules that bound the previous agent bind this one: owner time is the
binding budget; trade-study outcomes land as append-only `VO-` rows in
`docs/decisions.yaml`, and only the owner's word is `by: brian`; `docs/prereg.md` is
hash-pinned (VO-021, VO-077) and a test guards it; third-party files are never
committed; seeds are pinned and scored numbers must reproduce byte-identically; after
the founding commits, every change is a PR, merged on green.

**docs/kickoff.md, docs/plan.md, docs/gates/G1–G4.md.** The program ran to the end: G1
pass (map), G2 kill (clusters, by the pre-agreed rule), G3 pass under amendments A5/A6
(recognizer confidence), G4 "not calibrated" (known-answer arm). The writeup of
2026-10-30 states each with its qualifiers.

**docs/decisions.yaml — VO-001 to VO-083.** The last row, VO-083, is the findings log:
17 reporting errors to the end of G4, each corrected on the record. Appending `VO-`
rows with `by: obvious` is the established channel for findings — the audit extends it.

**results/map-v0/summary.json + GitHub releases.** Verified the full map's gated rate is
0.045939 (5,509 of 119,921), matching the brief and the G1 row. The `map-v0` and
`map-v0-test` releases exist; their `SHA256SUMS` pins `summary.json` as `df901b57…`, the
same digest `results/g1/checks.json` records — the committed summary and the published
release agree. The released per-column TSVs carry `locus, column, tier, class, flag,
contributing, gated` and deliberately no readings or codes (VO-028, G1-7): together the
readings would reconstruct the transliterations.

**The G2–G4 weights gap.** G2, G3 and G4 scored numbers all require the fine-tuned
Kraken model (`build/model/20261027/best_0.9452.safetensors`, sha256 `25ed687c…`, pinned
in VO-040/VO-052/VO-078). It is not committed, not in `snapshot/manifest.sha256`, and
the snapshot GCS bucket answers 403 without credentials — which the brief forbids
obtaining or creating. G4's 1,800 rendered PNGs are likewise kept on the owner's machine
(VO-082). Inference itself is not the barrier; weight availability is.

**README status.** `README.md` still says "Status: formulation (F0). Nothing is built
yet." — stale against the finished program, and the brief requires the status current.

**Flagged for the audit, not yet a finding.** The writeup says the leave-{ZL, IT}-out
rate is 3.61%; `summary.json` has 0.036196, which rounds to 3.62. Recorded as an
inference to check with a script during the audit, alongside every other figure.

## Build · Reproduction

A fresh-clone path that proves what the hardware here can prove, and honestly lists the
rest.

### What runs here

`make reproduce` (new target) runs, from a fresh clone:

- `uv sync --locked` — Python 3.12 as `.python-version` pins.
- `make snapshot` — fetches the third-party inputs from voynich.nu, Yale IIIF and the
  pinned Hugging Face commit, and verifies every byte against `snapshot/manifest.sha256`.
- `make map` — deterministic (~80 s), then `build/map/summary.json` is byte-diffed
  against `results/map-v0/summary.json` and against the `map-v0` release's
  `SHA256SUMS`. The nine published per-column TSVs are diffed the same way.
- `make g1` (~5 min, needs `cc` for the `ivtt` oracle) — regenerates
  `results/g1/checks.json`: determinism, the parser differential against `ivtt`, and
  injected-perturbation recovery.

### What does not run here, and why

| Scored numbers | Why not run |
|---|---|
| G2 (cluster entropy gaps), G3 (AUROCs, ECE, CER), G4 (CER, ECE) — gate results plus their seed-spread runs | Each requires the fine-tuned Kraken model, sha-pinned in VO-040, VO-052 and VO-078, which is neither committed nor fetchable: the snapshot bucket answers 403 without credentials, and the brief forbids cloud resources and GPU work. G4 additionally needs the 1,800 rendered PNGs kept on the owner's machine (VO-082). |

This list ships in the README's Reproduce section next to the reproduction commands, so
a reader can see at a glance which numbers a fresh sandbox proves and which it must take
on the pinned record. Reversal condition: if the owner later makes the pinned weights
fetchable (e.g. added to `snapshot/sources.toml` with sha256 pins), the reproduction
extends to G2–G4 on CPU and the list shrinks.

### CI proof of the H1 map

A new `map` job runs on every pull request and push to main: fetch the map's inputs (the
five STA transliterations, `bitrans/STA-aaa.bit`, `ivtt.c` — not the ~150 page images),
verify them against the manifest, `make map`, and byte-diff `summary.json` against
`results/map-v0/summary.json`. To make that cheap, `snapshot fetch` and `snapshot
verify` gain a path filter so a caller fetches and checks a subset. The job needs no
secrets: every input is a public URL.

## Build · Writeup audit

Every figure in `docs/writeup.md` traced to where it came from, with a script doing the
matching and a human-readable table as the deliverable.

A script extracts each number from the writeup — headline rates, intervals, counts, the
pairwise table, per-level ECEs, hours — and checks it against the committed results
(`results/g1`–`g4`, `results/a5/coverage.json`, `results/map-v0/summary.json`) and
against `docs/decisions.yaml`. The output is `docs/audit.md`: one row per writeup
figure, naming its source file and key, and the verdict (match / mismatch /
untraceable).

Discrepancies and untraceable figures become findings: appended `VO-` rows in
`docs/decisions.yaml` (append-only, dated, sourced, `by: obvious`), and a corrections PR
that proposes the writeup edits, each correction citing its `VO-` id. The writeup's
numbers are never edited outside that PR, and the PR body carries the full corrections
table so the owner reviews every change in one place.

> **Untouchable (invariant):** `docs/prereg.md` is not edited — it is hash-pinned
> (VO-077) and a parse test guards it; a change there would be an amendment only the
> owner approves. Gate packets (`docs/gates/*.md`) are the historical record: figures
> the writeup took from a gate are audited against the gate's own committed result
> files, not rewritten.

The README's stale status line ("formulation (F0). Nothing is built yet.") is corrected
in its own small PR, so the repo's front door matches what actually ran.

## Build · Map explorer

The H1 disagreement map is a table of 119,921 glyph columns across 227 folio pages; the
writeup says the right way to read it is "find where the sources disagree and look there
first". A static explorer makes that a click instead of a spreadsheet.

### Shape

A generator, `src/voynich_ocr/explorer.py` plus a `make explorer` target, reads the
published map outputs (the nine per-column TSVs and `summary.json`) and emits static
HTML to `build/explorer/`: an index page (headlines, the pairwise difference matrix from
`summary.json`, a legend for classes and tiers), a page per folio (the per-locus strip
of each line, colored by disagreement class, with flags and contributing sources), and a
small page per glyph column — the 119,921 "per glyph" pages — showing its class, tier,
flags and contributors with links up to the folio and out to the Beinecke image and the
voynich.nu sources. Buildless: one inline stylesheet, no framework, no build step; the
generated copy is served from this project's sandbox at a persistent hosted URL and is
not committed to the repo.

> **What the explorer must not redistribute (invariant):** The explorer renders only the
> published map data — the exact files the releases already publish under CC BY 4.0:
> classes, tiers, flags, contributors, counts. No readings, no codes, no transliteration
> text, and no manuscript images, linked instead to the Beinecke IIIF source and
> voynich.nu. The alternative — rendering the five per-source readings from a local
> `make map` run — was rejected: together they reconstruct the transliterations, which
> VO-009 and G1-7 forbid pending the authors' permission. That choice caps the
> per-glyph page at the column's locus and index rather than a glyph token, since token
> identity lives only in the unpublished readings.

### Evidence

Playwright drives the served site and captures screenshots at 1280px and 390px (index,
one folio, one glyph page); axe runs against the same pages and must pass with no
violations. A grep over `build/explorer/` confirms no transliteration bytes and no image
assets made it in. The screenshots and axe output are attached to the explorer PR.

## Verification

Each pass criterion in the brief, with the evidence that will stand behind it.

| Brief pass criterion | Proven by |
|---|---|
| Reproduce scored numbers that can run on CPU | `make reproduce` runs end-to-end from a fresh clone on the sandbox; `summary.json` and the nine published TSVs are byte-identical to `results/` and the release digests; `results/g1/checks.json` regenerates with the same digests. The commands and the not-run list (weights) land in the README's Reproduce section. |
| CI proves the H1 map on every PR | A PR touching nothing map-related still runs the new `map` job green: subset fetch → manifest verify → `make map` → byte-diff against `results/map-v0/summary.json`. |
| Numbers needing a GPU are listed, with reasons, and not run | The README not-run table names the G2–G4 numbers, the pinned weights they need (VO-040/VO-052/VO-078), and why they cannot run here; no GPU or cloud resource is created. |
| Writeup audit, discrepancies as VO- rows, corrections in a PR | `docs/audit.md` has a row for every figure in `docs/writeup.md` with its source and verdict; each discrepancy has an appended `VO-` row and a line in the corrections PR; the writeup diff shows no edit that lacks one. `prereg.md`'s guard test stays green. |
| Map explorer at a URL, no redistribution | The hosted URL serves the generated site; Playwright screenshots at 1280px and 390px exist; axe passes on the checked pages; a grep of the output finds no readings, codes, or images — links only, with CC BY 4.0 attribution. |
| CI green on main; README status current | Latest check run on main green after the merges; README states the finished program and the reproduction status. |

## Delivery

Three small PRs to main, each independently mergeable and merged when green, per
AGENTS.md and the brief's own words. Nothing is batched into one large PR, and the
repo's conventional-commit subject plus `Refs:` trailer format is kept.

| PR | Contents | Why this order |
|---|---|---|
| 1 · Audit and status | `docs/audit.md`, appended `VO-` rows, the writeup corrections citing them, and the README status line fix. | First, because the audit validates the numbers the other PRs' acceptance criteria quote. |
| 2 · Reproduction | Path filter for `snapshot fetch/verify`, the `make reproduce` target, the CI `map` job, and the README Reproduce section with the not-run table. | Standalone code; its CI job then protects PR 3's changes too. |
| 3 · Explorer | `src/voynich_ocr/explorer.py`, the `make explorer` target, and the hosted-URL verification evidence (screenshots, axe output). | Last, so its site is generated from outputs PR 2's job re-verifies continuously. |

Status comments tagged `[voynich-ocr]` go to thelemurcodes/kit-booking#21 three times:
at spec-ready (this approval), at the first PR merge, and when the program is done.

## Locked decisions

Committed before the build starts:

- The explorer renders only the published no-readings map data (VO-028): no readings,
  no codes, no transliteration text, no embedded images — links to Beinecke and
  voynich.nu instead.
- G2–G4 scored numbers are not re-run: their reasons are recorded in the README, and no
  GPU, cloud resource, or credential is created for them.
- `docs/prereg.md` is never edited by this program.
- Every `docs/decisions.yaml` row this program writes is append-only, dated, sourced,
  and `by: obvious`.
- Writeup numbers change only through the corrections PR, each edit citing its `VO-` id.
- Small PRs to main, merged when green; conventional-commit subjects; seeds stay
  pinned; no scored number is computed against ZL alone.
- This spec is the program's single owner decision. After approval, a decision is
  raised only where the build must depart from this spec.

### The one open question, folded into the approval

If the owner wants the G2–G4 numbers reproduced too, the way to unblock it is to make
the pinned weights fetchable — for example, adding `best_0.9452.safetensors` (sha256
`25ed687c…`) to `snapshot/sources.toml` with its digest, or making the bucket readable.
Until then, the spec's default stands: those numbers are listed as not run, with
reasons, exactly as the brief asks. Approving this spec approves the default; commenting
otherwise on the approval amends it before any work starts.

Publishing the writeup and any outreach to the Beinecke or the transliteration authors
remain the owner's actions and are outside this program.
