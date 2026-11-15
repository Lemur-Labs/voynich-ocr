# Decisions — the Obvious project

Exported 2026-11-15. This file covers the decisions made **in the Obvious project**
(the publish-readiness initiative, 2026-11-13 to 2026-11-14). Owner decisions are quoted
as such; the builder's own choices are marked **builder proposal**.

The research program's own decision log — VO-001 through VO-084, owner rows `by: brian`,
agent rows `by: claude`/`by: obvious` — is the repository's append-only
[docs/decisions.yaml](../decisions.yaml) and is not duplicated here. It remains the
authoritative record for anything predating or inside the research program.

## Owner decisions

**2026-11-13 — The brief (owner-authored, quoted).** The owner set the goal ("take
Lemur-Labs/voynich-ocr from 'writeup drafted for owner review' to ready to publish"),
the pass criteria (reproduction, writeup audit, map explorer, CI green), and the
must-nots: "Do not edit `docs/prereg.md`… Never write `by: brian`. Do not run GPU work
or create cloud resources… Do not make the repo public, and do not post to
voynich.ninja or contact anyone. Publishing is the owner's." Owner time was capped at
1.1 of 4 remaining hours, reserved for review and the 2026-11-23 score. Full text:
[specs/brief.md](specs/brief.md).

**2026-11-13 (~23:01 UTC) — The spec was approved.** The owner approved the Obvious
blueprint `voynich-ocr spec` (the Obvious task "Approve the voynich-ocr spec" was
completed 2026-11-13T23:01:48Z). By approving, the owner accepted the spec's defaults,
including the folded open question: G2–G4 scored numbers are listed as not run (weights
unfetchable) unless the owner later makes the pinned weights fetchable. Full text:
[specs/spec.md](specs/spec.md).

**2026-11-15 — Retirement and export (owner decision, relayed by the owner's
engineering agent).** "This project is being retired from the Obvious workspace and
archived. Nothing is being deleted on GitHub, and it may be revived later from what you
export now." All other work in the project stopped; the only action taken was this
docs-only export PR. The standing pause notice is at
[thelemurcodes/kit-booking#21](https://github.com/thelemurcodes/kit-booking/issues/21#issuecomment-6870603456).

## Builder proposals

Choices the Obvious agent made under the approved spec, with the owner's approval of the
spec as their warrant. Dates are when the choice was committed (spec 2026-11-13; builds
2026-11-13 to 2026-11-14).

- **Three-PR delivery order** — audit first (it validates the numbers the other PRs
  quote), then reproduction, then the explorer. Per the spec's Delivery table.
- **Audit as a script plus a table** — `src/voynich_ocr/audit.py` recomputes every
  writeup figure from its source and writes `docs/audit.md`; discrepancies become
  `VO-` rows. Result: 55/55 match, no writeup corrections needed (VO-084).
- **Not-run list instead of partial reproduction** — G2–G4 numbers stand on the pinned
  record, documented in the README, because the fine-tuned weights (sha256 `25ed687c…`)
  are unfetchable without credentials the project must not create. Recorded with the
  reversal condition (make the weights fetchable and the list shrinks).
- **Explorer renders only published no-readings data** — classes, tiers, flags,
  contributors, counts; no readings, codes, transliteration text or images. Rendering
  the per-source readings was rejected: together they reconstruct the transliterations
  (VO-009, G1-7). Per-glyph pages carry locus and index, not a glyph token.
- **G1 57/57 with a documented delta** — the reproduced `checks.json` matches the
  committed one on 57/57 shared keys; the remaining delta dates from the
  prereg-amendment era and is documented rather than hidden (PR #45).
- **Explorer hosting on the project sandbox** — the generated site is served from the
  Obvious project sandbox at a persistent hosted URL rather than committed to the repo,
  per the brief's own instruction. This creates the one infrastructure dependency
  listed in [infrastructure.md](infrastructure.md).
