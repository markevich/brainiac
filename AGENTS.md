# Brainiac Agent Entrypoint

This repository is Brainiac: an AI-first local second-brain framework over plain files.

Before doing substantial work in this repository, load this context in order:

1. `README.md` — project summary and core roles.
2. `docs/brainiac-intro.md` — the shortest accurate system model and glossary.
3. `docs/concept.md` — conceptual architecture and non-goals.
4. `docs/development-plan.md` — current implementation roadmap.
5. `docs/context-brief.md` — historical context and original design reasoning.
6. `operator.md`, `docs/operator-context.md`, and `docs/operator-playbook.md` only if the task is about Jarvis operating on a vault, not developing Brainiac itself.

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
- Keep write operations explicit, logged, and policy-checked.
- Do not build an Obsidian clone.
- Do not introduce autonomous rewrite behavior before dry-run/review workflows exist.
- Use `PYTHONPATH=src python3 -m brainiac <command>` for CLI runs in this repo.
- Use `uv run python -m unittest tests.test_maintenance tests.test_duplicates` for the default test pass; prefer `unittest` here unless the task explicitly needs `pytest`.

## Operator Mode

Use this mode when Jarvis is working with a user's vault through Brainiac.

Rules:

- Do not scan the entire vault unless explicitly asked.
- Prefer `brainiac index info` before `brainiac scan`.
- Prefer bounded search/inspect/read tools once implemented.
- Treat Markdown, SQLite, JSON, YAML, CSV, and source assets as truth.
- Treat generated HTML as presentation only.
- Ask before mutating sensitive domains such as health, family, finance, legal, credentials, or private operational data.
- Log every write operation.
- Treat `docs/operator-playbook.md` as the default procedural runbook for vault operations.

## Current Repository Shape

```text
config/
  vault.example.yml
  routing.example.yml
  vault.yml        # local, gitignored
  routing.yml      # local, gitignored
  policies.yml
docs/
  concept.md
  context-brief.md
  development-plan.md
  operator-context.md
  source-takeaways.md
src/brainiac/
  cli.py
  config.py
  scanner.py
  markdown.py
  index.py
  report.py
tests/
memory/
  generated/
  queue/
  index/
  logs/
operator.md
```
