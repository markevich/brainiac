# Brainiac

AI-first local second brain framework over plain files.

Brainiac is a generic personal knowledge backend for AI agents. It is not an Obsidian clone and not a replacement for Markdown notes. It is a memory, retrieval, routing, and synthesis layer that can sit on top of an existing local vault.

## Core Idea

```text
Vault with Markdown / SQLite / JSON / assets
        |
        v
Disposable indexes and bounded retrieval tools
        |
        v
AI operator that searches, routes, dedupes, synthesizes, and writes safely
        |
        v
Optional views: Obsidian, CLI, local HTML dashboards
```

## Roles

- `Obsidian` is the editor and human-facing vault UI.
- `Markdown/SQLite/JSON` are source-of-truth formats.
- `Brainiac` is the local memory/retrieval backend.
- `Jarvis or another agent` is the operator that talks to Brainiac.
- `HTML` is a generated presentation layer, not durable truth.

## First Principle

The AI should never load the whole vault or the whole index into context.

It should call bounded tools:

```text
brain.search(query, filters)
brain.inspect(path)
brain.read(path, section?)
brain.related(path_or_text)
brain.route(content)
brain.find_duplicates(content)
brain.neighborhood(path, depth, max_nodes)
```

Those tools return compact candidates, snippets, paths, scores, and reasons. Full files are read only when needed.

## Current Status

This repository starts as a concept and planning skeleton. The first implementation milestone is a small local CLI indexer over one Obsidian-style vault.

See:

- [docs/concept.md](docs/concept.md)
- [docs/development-plan.md](docs/development-plan.md)
- [operator.md](operator.md)

