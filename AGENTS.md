# Brainiac Agent Entrypoint

This repository is Brainiac: an AI-first local second-brain framework over plain files.

Before doing substantial work in this repository, load this context in order:

1. `README.md` — project summary and core roles.
2. `docs/context-brief.md` — condensed context from the original design discussion.
3. `docs/concept.md` — conceptual architecture and non-goals.
4. `docs/development-plan.md` — current implementation roadmap.
5. `operator.md` and `docs/operator-context.md` only if the task is about operating on a vault, not developing Brainiac itself.

## Development Mode

Use this mode when implementing Brainiac itself.

Rules:

- Keep Brainiac generic. Do not hard-code Softswiss or Jarvis-specific assumptions.
- Prefer CLI-first implementation before MCP, Obsidian plugin, or background daemon.
- Treat indexes as disposable caches rebuildable from source files.
- Start with structural and lexical retrieval before embeddings.
- Keep write operations explicit, logged, and policy-checked.
- Do not build an Obsidian clone.
- Do not introduce autonomous rewrite behavior before dry-run/review workflows exist.

## Operator Mode

Use this mode when Brainiac or an AI operator is working with a user's vault.

Rules:

- Do not scan the entire vault unless explicitly asked.
- Prefer bounded search/inspect/read tools once implemented.
- Treat Markdown, SQLite, JSON, YAML, CSV, and source assets as truth.
- Treat generated HTML as presentation only.
- Ask before mutating sensitive domains such as health, family, finance, legal, credentials, or private operational data.
- Log every write operation.

## Current Repository Shape

```text
config/
  vault.yml
  routing.yml
  policies.yml
docs/
  concept.md
  context-brief.md
  development-plan.md
  operator-context.md
  source-takeaways.md
memory/
  synthesis/
  generated/
  queue/
  index/
  logs/
operator.md
```

