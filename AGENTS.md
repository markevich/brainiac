# Brainiac Agent Entrypoint

This repository is Brainiac: an AI-first local second-brain framework over plain files.

Before doing substantial work in this repository, read `brainiac.md`. It is the
single shared product and operating contract.

Read `docs/development-plan.md` only when discussing roadmap, choosing the
next implementation work, or changing phase status.

When operating a vault, follow `brainiac.md` and then its bounded bootstrap
sequence; do not load a second operator playbook.

## Development Mode

Use this mode when implementing Brainiac itself.

Rules:

- Keep Brainiac generic.
- Treat Jarvis as the default operator name, not as a dependency on any existing Jarvis project.
- Do not import session flows, banners, or project-specific instructions from other Jarvis repositories.
- Do not commit hardcoded user-specific absolute paths, personal usernames, private organization names, or local machine paths into tracked docs, logs, configs, tests, or source files. Use placeholders or generic descriptions instead.
- Prefer CLI-first implementation before MCP, Obsidian plugin, or background daemon.
- Treat indexes as disposable caches rebuildable from source files.
- Start with structural and lexical retrieval before embeddings.
- Do not introduce vault write commands before an explicit review workflow exists.
- Do not build an Obsidian clone.
- Do not introduce autonomous rewrite behavior before dry-run/review workflows exist.
- Use `PYTHONPATH=src python3 -m brainiac <command>` for CLI runs in this repo.
- Use `uv run python -m unittest discover -s tests` for the default test pass; prefer `unittest` here unless the task explicitly needs `pytest`.

## Operator Mode

Use this mode when Jarvis is working with a user's vault through Brainiac.

Rules:

- Do not scan the entire vault unless explicitly asked.
- A scan is also allowed after a user-confirmed vault edit when it is needed to
  refresh bounded retrieval; include that refresh in the proposed change-set.
- Prefer `brainiac index info` before `brainiac scan`.
- Prefer bounded search/inspect/read tools once implemented.
- Treat Markdown, SQLite, JSON, YAML, CSV, and source assets as truth.
- Treat generated HTML as presentation only.
- Ask before mutating sensitive domains such as health, family, finance, legal, credentials, or private operational data.
- The current CLI has no vault write commands; preserve that boundary until a review workflow exists.
- Treat `brainiac.md` as the default procedural runbook for vault operations.

## Current Repository Shape

```text
config/
  brainiac.yml     # local, gitignored
brainiac.md         # tracked shared LLM contract
brainiac_me.md      # local, gitignored personal context
.state/             # local, gitignored setup/update state
docs/
  development-plan.md
src/brainiac/
  cli.py
  config.py
  scanner.py
  markdown.py
  index.py
  bootstrap.py
  para.py
tests/
memory/
  index/
```
