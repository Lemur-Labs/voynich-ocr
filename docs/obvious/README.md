# Obvious project export — voynich-ocr

This directory preserves the Obvious workspace records for the publish-readiness
initiative on this repository, exported on **2026-11-15** when the Obvious project
was retired and archived. Nothing was deleted from GitHub; this export is what a
revival would start from.

## What this project is

An Obvious Autobuild initiative ("voynich-ocr") that took Lemur-Labs/voynich-ocr
from "writeup drafted for owner review" to ready to publish, through three
testable claims about work that already existed:

1. **Reproduction** — every scored number that can run on CPU reproduces
   byte-identically from a fresh clone, and a CI job proves the H1 disagreement
   map on every pull request.
2. **Writeup audit** — every figure in `docs/writeup.md` is traced to a results
   file or a decisions row, with discrepancies recorded as `VO-` rows and
   corrections proposed in a PR, never silently edited.
3. **Map explorer** — a static, buildless explorer at a hosted URL showing where
   the five transliterations disagree, without redistributing the transliteration
   files or the Beinecke images.

The underlying research program (gates G1–G4) had already finished before this
initiative started; its charter, plan, gate records and writeup live in this
repository itself (`docs/kickoff.md`, `docs/plan.md`, `docs/gates/`,
`docs/writeup.md`) and are not duplicated here.

## Goal and pass criteria

From the owner's brief ([specs/brief.md](specs/brief.md)):

- **Reproduction.** From a fresh sandbox (`make snapshot` fetches from voynich.nu
  and checks the SHA-256 manifest), every scored number that can run on CPU
  reproduces byte-identically against `results/`, including the H1 map
  (`results/map-v0/summary.json`, gated rate 0.045939). A CI job proves the H1 map
  on every PR. Numbers that need a GPU are listed with the reason, and are not run.
- **Writeup audit.** Every figure in `docs/writeup.md` is traced to a results file
  or a decisions row. Discrepancies go in as findings: `VO-` rows appended to
  `docs/decisions.yaml` with `by: obvious`, corrections proposed in a PR.
- **Map explorer.** A static, buildless page per glyph and per page, showing where
  the five transliterations disagree, generated from the published map outputs
  (CC BY 4.0). It must not redistribute the transliteration files or the Beinecke
  images: link to them instead. Served from the project sandbox's hosted URL and
  verified with Playwright screenshots at 1280px and 390px, with axe passing.
- CI is green on main, and the README status is current.

## Status at retirement (2026-11-15)

**Shipped — all three workstreams merged to main, post-merge CI green:**

- **PR #44** (merge `9adc352`) — writeup audit. 55/55 figures audited against
  `main 83b2915`: 55 match, 0 mismatch, 0 untraceable (`docs/audit.md`,
  `src/voynich_ocr/audit.py`, decision VO-084). No writeup correction was needed.
  README status corrected.
- **PR #45** (merge `a89ac9d`) — reproduction harness. Clean-tree `make reproduce`
  matched `summary.json` and all 8 published TSVs byte-for-byte against the
  release assets; `results/g1/checks.json` matched 57/57 shared keys (the
  prereg-amendment-era delta is documented); CI map job proves the H1 map on every
  PR; 219 tests passing.
- **PR #46** (merge `6ae6126`) — disagreement-map explorer. 129,218 pages
  generated from the published no-readings map outputs, zero boundary violations,
  no axe violations, six Playwright screenshots attached to the PR. Served at
  https://1qn0cntysr-8765.hosted.obvious.ai — see
  [infrastructure.md](infrastructure.md) for what that dependency means.

**Half-built / not done:**

- G2–G4 scored numbers were **not** re-run. They need the fine-tuned Kraken model
  weights (sha-pinned in VO-040, VO-052, VO-078), which are neither committed nor
  fetchable: the snapshot GCS bucket answers 403 without credentials, and the
  brief forbids obtaining or creating cloud credentials. They stand on the pinned
  record, listed as not run in the README's Reproduce section. G4 additionally
  needs the 1,800 rendered PNGs kept on the owner's machine (VO-082).
- Publishing (the writeup, the voynich.ninja map post, reviewer invitations) is
  the owner's action and had not happened by retirement (VO-006, VO-062).
- The 2026-11-23 autonomy score, the program's final deliverable, was still ahead.

## How to revive

1. Read [specs/brief.md](specs/brief.md) (the owner's intent),
   [specs/spec.md](specs/spec.md) (the owner-approved spec), and the repository's
   `docs/decisions.yaml` (VO-001–VO-084, append-only).
2. Open items and pending decisions: [open-work.md](open-work.md).
3. External resources, for teardown or revival: [infrastructure.md](infrastructure.md).
4. The repo needs no rebuild to resume: `main` at `6ae6126` is the finished state;
   `make reproduce` and `make lint test` verify it from a fresh clone.
5. To extend reproduction to G2–G4, make the pinned weights fetchable — for
   example, add `build/model/20261027/best_0.9452.safetensors` (sha256
   `25ed687c…`) to `snapshot/sources.toml` with its digest. That was the one open
   question folded into the spec approval, and it reverses the not-run list.

## Files

| File | Contents |
|---|---|
| [README.md](README.md) | This overview |
| [specs/brief.md](specs/brief.md) | The owner's brief (verbatim) |
| [specs/spec.md](specs/spec.md) | The owner-approved spec (converted from the Obvious blueprint artifact) |
| [specs/autobuild-program-rules.md](specs/autobuild-program-rules.md) | Autobuild program rules in force (verbatim) |
| [decisions.md](decisions.md) | Decisions made in the Obvious project, with dates |
| [open-work.md](open-work.md) | Open tasks, PRs, pending decisions, known bugs and blockers |
| [infrastructure.md](infrastructure.md) | External resources this project created or uses |
