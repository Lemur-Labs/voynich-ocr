# Brief: voynich-ocr (brownfield research repo)

> Exported from the Obvious project on 2026-11-15 (artifact `voynich-ocr brief`,
> created 2026-11-13). Verbatim below; the owner wrote it.

**Goal.** Take Lemur-Labs/voynich-ocr from "writeup drafted for owner review" to ready to publish:
- every scored number reproduced independently;
- the writeup checked against the results;
- the disagreement map explorable at a URL.

The research program (gates G1 to G4) is finished. Read `AGENTS.md`, `docs/kickoff.md`, `docs/plan.md`,
`docs/decisions.yaml` and `docs/writeup.md` first. AGENTS.md's rules bind you exactly as they bound the previous agent.

**Hypothesis under test.** Obvious can work inside a pre-registered research repo without bending its rules: it can
reproduce scored ML results from pinned inputs and seeds, and find errors in a writeup rather than smooth them over.

**Pass criteria.**
- **Reproduction.** From a fresh sandbox (`make snapshot` fetches from voynich.nu and checks the sha256 manifest),
  every scored number that can run on CPU reproduces byte-identically against `results/`. This includes the H1 map
  (`results/map-v0/summary.json`, gated rate 0.045939) and whichever of G2 to G4 fit on CPU. A CI job proves the H1
  map on every PR. Numbers that need a GPU are listed with the reason, and are not run.
- **Writeup audit.** Every figure in `docs/writeup.md` is traced to a results file or a decisions row. Discrepancies
  go in as findings: append `VO-` rows to decisions.yaml with `by: obvious`, and propose corrections in a PR. Never
  silently edit the writeup's numbers.
- **Map explorer.** A static, buildless page per glyph and per page, showing where the five transliterations disagree,
  generated from the map outputs (CC BY 4.0). It must not redistribute the transliteration files or the Beinecke
  images: link to them instead. It is served from this project's sandbox hosted URL
  (`{projectId}-{port}.hosted.obvious.ai`) and verified with Playwright screenshots at 1280px and 390px, with axe
  passing.
- CI is green on main, and the README status is current.

**Must not.**
- Do not edit `docs/prereg.md` (it is hashed; a change is an amendment the owner approves).
- Never write `by: brian`.
- Do not run GPU work or create cloud resources (`gcloud`, the snapshot bucket, VMs).
- Do not make the repo public, and do not post to voynich.ninja or contact anyone. Publishing is the owner's.

**Owner time.** Owner time is the binding budget: 1.1 of 4 hours remain, and they are reserved for review and the
2026-11-23 score. Raise at most ONE decision, batched as a gate packet at the end, and log the owner minutes it asks
for.

**Constraints.** Only write to Lemur-Labs/voynich-ocr. Small PRs to main, which you merge when green, with
conventional-commit subjects. Python 3.12 with uv (`uv sync --locked`). Seeds stay pinned.

**Connected.** GitHub App on this repo. Egress to voynich.nu is open. No cloud credentials.
