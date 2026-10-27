# Working in this repository

Read `docs/kickoff.md`, `docs/plan.md` and `docs/decisions.yaml` before changing anything. The plan is the
specification; when code and plan disagree, raise it rather than picking one.

- Scope is the kickoff's deliverables. Decipherment, translation and hand-labeling glyphs are non-goals; the Naibbe
  arm is the only cipher work in scope.
- Owner time is the binding budget (four hours in total). Escalate only at a gate, batched into the gate packet; never
  mid-phase. Log every owner minute in the gate packet.
- Once `docs/prereg.md` is hashed at KDP-F, a change to it is an amendment with a stated reason, never an edit.
  Gate outcomes are computed by the pre-registered rule in code, not judged.
- A trade-study outcome lands as a `VO-` row in `docs/decisions.yaml`. Rows are append-only. Only the owner's word
  is `by: brian`.
- Third-party transliterations and images are fetched by script and checked against the SHA-256 manifest. They are
  never committed.
- Pin every RNG seed. A scored number must reproduce byte-identically from the snapshot.
- Founding commits go straight to `main`; after that every change is a pull request. Conventional-commit subjects.
- No result is scored against ZL alone.
