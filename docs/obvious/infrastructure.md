# Infrastructure — external resources

Exported 2026-11-15. Everything the Obvious project created or used, so it can be torn
down or revived. Secret names are listed; **values are never recorded here** — this
project held no secret values outside the workspace's own store, and nothing below
needs one to rebuild.

## GitHub

- **Repository** — [Lemur-Labs/voynich-ocr](https://github.com/Lemur-Labs/voynich-ocr),
  public since 2026-10-27 (VO-026). Default branch `main`; finished state at `6ae6126`.
  Not deleted by the retirement.
- **GitHub releases** — `map-v0` (per-column class/tier/flag/contributing/gated TSVs +
  `summary.json`, no readings or codes per VO-028) and `map-v0-test` (the 40 test
  pages' rows released after G3, same columns, per VO-064). Both carry `SHA256SUMS`.
- **GitHub Actions CI** — `test` and `map` jobs; the `map` job proves the H1 map on
  every PR (added in PR #45). Needs no secrets; every input is a public URL.
- **GitHub App** — connected to this repository by the Obvious workspace (the brief's
  "Connected" line). Managed at the workspace level, not project level.

## External data sources (fetched by script, verified against `snapshot/manifest.sha256`, never committed)

- **voynich.nu** — transliterations (ZL, Takahashi/IT, Currier/CD, GC, FSG), STA files
  including `STA-aaa.bit`. Egress from the Obvious sandbox to voynich.nu was open by
  workspace policy.
- **Beinecke / Yale IIIF** — manuscript page images (177 pages with their own canvas;
  foldouts excluded per VO-030). Linked, never redistributed.
- **Hugging Face** — DINOv2 ViT-S/14 weights at a pinned commit (VO-012).
- **Greshko's naibbe-cipher** — vendored at pinned commit `719f2f4` into `data/raw/naibbe`
  via `snapshot/sources.toml`, sha-pinned (VO-016, VO-074).
- **Zandbergen's `ivtt`** — fetched and compiled as a local differential oracle, never
  vendored (VO-014).

## Cloud

- **GCS snapshot bucket** — referenced by the research plan (F0.1) as the snapshot
  destination. This Obvious project held **no credentials for it** (the bucket answered
  403 without them; the brief forbade obtaining or creating cloud credentials), so its
  name and state are not recorded in this project. Treat as the owner's resource, not
  the project's.

## Obvious project (prj_oB70fElv) — retired 2026-11-15

- **Hosted explorer service** — static disagreement-map explorer served from the
  project sandbox at **https://1qn0cntysr-8765.hosted.obvious.ai** (port 8765,
  tmux session `svc-8765`). **This dies with the sandbox.** Regenerate anywhere with
  `make map && make explorer` (runs `uv run python -m voynich_ocr.explorer`), then
  serve `build/explorer/` with any static file server. An Obvious iframe artifact
  (`voynich-ocr disagreement map explorer`, `art_oTuNLobG`) embeds the URL.
- **Project artifacts (4)** — `voynich-ocr brief` (`art_l5RxUtN0`, exported verbatim as
  [specs/brief.md](specs/brief.md)), `voynich-ocr spec` (`art_Ftfi5hlt`, exported as
  [specs/spec.md](specs/spec.md)), `Autobuild program rules` (`art_dMrnx9YP`, exported
  as [specs/autobuild-program-rules.md](specs/autobuild-program-rules.md)), and the
  explorer iframe above. The project archive keeps these; the exports here are the
  revival copy.
- **Repo sandbox** — Obvious sandbox computer `cmp_jSiZra9q` with the repo pre-cloned
  at `/home/user/work/voynich-ocr`. No state there is load-bearing; the repo and its
  branches live on GitHub.
- **External issue reference** —
  [thelemurcodes/kit-booking#21](https://github.com/thelemurcodes/kit-booking/issues/21)
  carried the program's `[voynich-ocr]` milestone comments and now the pause notice.
  Read-only from this project's side.

## Secrets

- **Created by this project: none.** No scored path needs a credential; the CI `map`
  job uses only public URLs.
- **Workspace-scope secrets available by name** (workspace-level, not project-created,
  and never used by this repository's CI): `ANTHROPIC_API_KEY`, `NODE_AUTH_TOKEN`,
  `RAILWAY_API_TOKEN`. Listed by name only because a revival should not assume any of
  them is project-specific.

## Teardown / revival checklist

- Teardown: archive the Obvious project (done 2026-11-15); the hosted service and repo
  sandbox stop with it; nothing in the repository depends on them. GitHub (repo,
  releases, CI, GitHub App) and the owner's own cloud resources (GCS bucket) persist.
- Revival: clone the repo, `uv sync --locked`, `make reproduce`, `make lint test` —
  that proves `main` intact. For the explorer UI, `make map && make explorer` and serve
  `build/explorer/`. To extend reproduction to G2–G4, make the pinned weights fetchable
  (see [open-work.md](open-work.md), pending decisions).
