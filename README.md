# voynich-ocr

Calibrated glyph recognition for the Voynich manuscript (Beinecke MS 408), scored against where the published
transliterations disagree rather than against any single one. Not a decipherment.

Status: formulation (F0). Nothing is built yet.

| | |
|---|---|
| [docs/kickoff.md](docs/kickoff.md) | The charter: bet, deliverables, non-goals, kill criteria. Input to the plan |
| [docs/plan.md](docs/plan.md) | Process, kickoff corrections, phases and gates, trade studies, open recommendations |
| [docs/decisions.yaml](docs/decisions.yaml) | Decisions in force, append-only |
| [AGENTS.md](AGENTS.md) | Rules for anyone, person or agent, working here |

Licensing: code is MIT ([LICENSE](LICENSE)); the writeup, the disagreement map and other generated outputs are
CC BY 4.0. Transliterations are © their authors and images are Beinecke public domain; neither is redistributed here.

## Reproduce

```
uv sync
make snapshot        # fetch third-party inputs into data/raw/ and check them against snapshot/manifest.sha256
make lint test
```

If an upstream file changes, `make snapshot` fails with the path. `make snapshot-pull` restores the pinned bytes from
the project's bucket.
