# Concept: AI-first local second brain

Brainiac lets an AI work with a local knowledge vault through bounded tools instead of loading whole folders into context.

```text
local vault -> disposable SQLite index -> bounded CLI tools -> operator -> optional views
```

## Principles

- Markdown, SQLite, JSON, YAML, CSV, and assets remain source of truth.
- Indexes are incremental caches and can be rebuilt.
- Retrieval is a tool call, not a prompt dump.
- Start with structural and lexical retrieval, not embeddings.
- Writes are explicit, policy-checked, and logged.
- Brainiac is not an Obsidian clone.

## Vault structure

Brainiac uses PARA as its canonical vault contract for new managed vaults: `Inbox/`, `Projects/`, `Areas/`, `Resources/`, and `Archive/`. `Brainiac/` is reserved for tool-owned state and generated artifacts. This is an opinionated product rule, not an automatic migration policy: an existing vault is changed only through a separately reviewed migration plan.

## Notes

Use `source` for ordinary content. Use an `umbrella` only when people need a compact map of related notes, categories, status, or selection rules. Keep any short conclusions in that umbrella instead of maintaining a second derived note type.
