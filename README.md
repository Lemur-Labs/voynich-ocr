# voynich-ocr

Calibrated glyph recognition for the Voynich manuscript (Beinecke MS 408), scored against where the published
transliterations disagree rather than against any single one. Not a decipherment.

Status: the G1–G4 research program is complete (G1 map pass, G2 cluster kill, G3 recognizer-confidence pass under amendments A5/A6, G4 not calibrated); see [docs/writeup.md](docs/writeup.md). Publish readiness is in progress.

| | |
|---|---|
| [docs/kickoff.md](docs/kickoff.md) | The charter: bet, deliverables, non-goals, kill criteria. Input to the plan |
| [docs/plan.md](docs/plan.md) | Process, kickoff corrections, phases and gates, trade studies, open recommendations |
| [docs/decisions.yaml](docs/decisions.yaml) | Decisions in force, append-only |
| [AGENTS.md](AGENTS.md) | Rules for anyone, person or agent, working here |

Licensing: code is MIT ([LICENSE](LICENSE)); the writeup, the disagreement map and other generated outputs are
CC BY 4.0. Transliterations are © their authors and images are Beinecke public domain; neither is redistributed here.

## Reproduce

From a fresh clone:

```
uv sync --locked
make reproduce        # snapshot → map → g1, byte-compared against the committed record
make lint test
```

`make reproduce` fetches the third-party inputs and verifies every byte against
[snapshot/manifest.sha256](snapshot/manifest.sha256), regenerates the disagreement map (`make map`, ~80 s) and the
G1 checks (`make g1`, ~5 min, needs a C compiler for the `ivtt` oracle), and byte-compares the results: `summary.json`
against [results/map-v0/summary.json](results/map-v0/summary.json) and against the digest the
[map-v0 release](https://github.com/Lemur-Labs/voynich-ocr/releases/tag/map-v0)'s SHA256SUMS pins, and the published
per-column TSVs against the same release assets. The regenerated `results/g1/checks.json` matches the committed file
on every key it shares — the parser differential against `ivtt`, determinism, injected-perturbation recovery, and all
map digests — and its only additions are the `published-test` digests and the void-share key named for the coverage
minimum that prereg amendment A5 moved (0.72 → 0.56) after the G1 record was committed; anything else fails the
target. CI runs the map half of this on every pull request.

If an upstream file changes, `make snapshot` fails with the path. `make snapshot-pull` restores the pinned bytes from
the project's bucket. `snapshot fetch` and `snapshot verify` accept a repeatable `--path=DIR-OR-FILE` filter, so a
caller can fetch and check a subset (the map needs only the STA transliterations, `bitrans/STA-aaa.bit` and
`ivtt/ivtt.c` — not the ~150 page images).

### Not run here

The G2–G4 scored numbers depend on the fine-tuned Kraken model
`build/model/20261027/best_0.9452.safetensors` (sha256 `25ed687c…`), which is not committed and not fetchable: it
lives in a private bucket that answers 403 without credentials, and this program creates no new cloud resources and
does no GPU work. G4 additionally needs the ~1,800 rendered PNGs kept only on the owner's machine (VO-082).

| Scored numbers | Weights pinned by | Why not run |
|---|---|---|
| G2 cluster entropy gaps ([results/g2/result.json](results/g2/result.json)) | VO-040 | Weights unavailable (above) |
| G3 AUROCs, ECE, CER ([results/g3/result.json](results/g3/result.json)) | VO-052 | Weights unavailable (above) |
| G4 CER, ECE on Naibbe synthetic ([results/g4/result.json](results/g4/result.json)) | VO-078 | Weights unavailable; the rendered PNGs are kept only on the owner's machine (VO-082) |

These extend if the weights ever become fetchable (for example pinned with their sha256 in
[snapshot/sources.toml](snapshot/sources.toml)): the same commands would then run them on CPU.
