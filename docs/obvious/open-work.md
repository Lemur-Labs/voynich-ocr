# Open work at retirement (2026-11-15)

Everything below was verified on 2026-11-15 from the Obvious task tree and GitHub.

## Open tasks in the Obvious project

None. All six tasks are terminal: the initiative root
("voynich-ocr: reproduce results, audit writeup, ship map explorer") and its three build
tasks are completed; the owner's spec-approval task is completed; one duplicate coder
task was cancelled at dispatch.

## Open pull requests

None. `gh pr list --state open` on Lemur-Labs/voynich-ocr returned empty on
2026-11-15. The three program PRs (#44, #45, #46) are squash-merged with post-merge CI
green (runs 43527348081, 43531353020, 43535888868).

## Pending decisions (the owner's)

- **Publishing and outreach** — the writeup, the voynich.ninja map post and the ten
  buyer-test messages, and reviewer invitations, are the owner's actions (VO-006,
  VO-062). None had happened by retirement. The map post was owed since G1 (VO-026) and
  drafted-but-unsent per VO-062.
- **Weights fetchability** — whether to make the pinned G2–G4 model weights fetchable
  (e.g. add `best_0.9452.safetensors`, sha256 `25ed687c…`, to `snapshot/sources.toml`
  with its digest, or make the snapshot bucket readable). This was the one open
  question folded into the spec approval; until it is answered, G2–G4 numbers stay on
  the pinned record and the README's not-run list stands.
- **The 2026-11-23 autonomy score** — the program's final deliverable, on the behaviours
  logged in VO-045, VO-063 and VO-083. Not yet scored at retirement.
- **Owner time remaining** — 1.1 of 4 hours as of 2026-10-30 (VO-081), reserved for the
  final writeup review and the 2026-11-23 score.

## Known bugs and blockers

- **Pinned model weights unfetchable** — `build/model/20261027/best_0.9452.safetensors`
  (sha256 `25ed687c…`, VO-040/VO-052/VO-078) is neither committed nor in
  `snapshot/manifest.sha256`, and the snapshot GCS bucket answers 403 without
  credentials the project was forbidden to obtain or create. Blocks re-running G2–G4
  scored numbers outside a machine that already has the weights.
- **G4 rendered PNGs exist only on the owner's machine** — 1,800 PNGs, digest
  `609310d3…` (VO-082), git-ignored and not committed. Blocks G4 reproduction entirely;
  `h4 --gate` regenerates them from the frozen configuration if needed.
- **Hosted explorer URL dies with the sandbox** —
  https://1qn0cntysr-8765.hosted.obvious.ai serves from the Obvious project sandbox and
  stops serving when the sandbox shuts down with retirement. Recovery is one command on
  any machine: `make map && make explorer`, then serve `build/explorer/` (see
  [infrastructure.md](infrastructure.md)).

## Historical notes (closed, listed for completeness)

- Prereg amendment drafts `docs/prereg-A4-draft.md`, `prereg-A7-draft.md` and
  `prereg-A8-draft.md` remain as files, but A4, A7 and A8 were all appended to
  `docs/prereg.md` (VO-077, VO-069); the drafts are historical, not pending.
- The program's `[voynich-ocr]` milestone comments went to
  [thelemurcodes/kit-booking#21](https://github.com/thelemurcodes/kit-booking/issues/21)
  at spec-ready, first merge and done; the thread now carries the retirement pause
  notice.
