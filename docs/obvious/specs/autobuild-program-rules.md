# Autobuild program rules

> Exported from the Obvious project on 2026-11-15 (artifact `Autobuild program rules`,
> created 2026-11-13). Verbatim below. These rules applied to every program created
> from the Autobuild template; a program's own overview and specs added to them, and
> where they conflicted, the program's specs won.

These rules apply to every program created from this template. A program's own overview and specs add to them;
where they conflict, the program's specs win.

## Repositories
- Work only in the repository named by the program. If none is connected, propose a name and what must be
connected as a decision for the human, and continue with work that does not need it.
- Never install on, read from, or open PRs against Lemur-Labs/kit-drills, Lemur-Labs/m1rror-drills or
Lemur-Labs/m1rror-drills-evidence.

## Definition of done
- Done means it runs: a command or URL works from a fresh clone, with a smoke test against the real backend and
screenshots for any UI. A library with only an in-memory adapter is a milestone, not done.
- Every port ships with its real adapter in the same initiative, and its contract tests run against both.
- Nothing stays fake unless the spec says it may. Anything not supplied by the spec is labelled a placeholder in
the product and the docs.
- Keep the README status current in every PR that changes what works.

## Decisions
- Only decisions written in the program's specs are owner decisions. Anything you choose is recorded in
docs/decisions/ as "proposed by the builder", with the rejected alternatives, never as an owner decision.
- If a spec is ambiguous or conflicts with these rules, raise a decision for the human instead of guessing.

## Build environment
- Use the runtime versions the spec pins. Do not downgrade dependencies to fit an older runtime; install the
pinned runtime instead.
- Provide scripts/bootstrap.sh that installs every tool the tests need. Name any suite that cannot run in the
sandbox in AGENTS.md, and run it in CI.
- Monorepo task runners pass HTTPS_PROXY, NO_PROXY, NODE_USE_ENV_PROXY and NODE_EXTRA_CA_CERTS through to child
tasks.
- Never put secrets in code, logs, fixtures or PR text.

## Pull requests
- Small PRs, one executable each, with tests passing and a body that states what was deferred and why.
