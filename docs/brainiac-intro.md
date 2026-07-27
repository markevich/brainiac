# Brainiac Intro

Brainiac is an AI-first local retrieval and maintenance backend over a plain-file vault. Markdown and structured files are truth; SQLite is a rebuildable retrieval cache.

## Vault layout

The required layout for a new Brainiac-managed vault is PARA: `Inbox/`, `Projects/`, `Areas/`, `Resources/`, and `Archive/`. The disposable SQLite index stays in the local Brainiac workspace, outside the vault. Existing vaults require an explicit migration plan; Brainiac must not move them automatically.

Create a new managed vault with `brainiac init --vault-root /path/to/new-vault`. The command refuses a non-empty destination and refuses to overwrite the local vault config.

For a vault with `vault.layout: para`, `maintenance report` reports missing roots. `route` blocks new write suggestions until those violations are fixed. Read-only indexing and retrieval remain available. Route candidates are derived from indexed paths and IDF-weighted note evidence; there is no routing map to keep in sync.

## Note roles

- `source` is the default role for every new note: facts, captures, cards, tasks, and observations.
- `umbrella` is an explicit navigation note. It links source notes, groups them, and may contain short working rules such as “how to choose”.

There is no derived-note role. Do not create a second summary layer merely because several notes are related.

## Default operator loop

1. Check index freshness.
2. Search, inspect, and read bounded context.
3. Create or update a `source` note.
4. Inspect its backlinks. If an umbrella links to it, decide whether the change affects that umbrella’s navigation, categories, status, rating, or choice rules.
5. Suggest an umbrella update only when it does. If no umbrella exists, propose one only for a real navigation problem; never create it automatically.

## Core relationship

```text
source files = truth
SQLite index = disposable retrieval cache
umbrella notes = human navigation and compact working guidance
Jarvis = operator
```
