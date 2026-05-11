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
Jarvis searches, routes, dedupes, synthesizes, and writes safely
        |
        v
Optional views: Obsidian, CLI, local HTML dashboards
```

## Roles

- `Obsidian` is the editor and human-facing vault UI.
- `Markdown/SQLite/JSON` are source-of-truth formats.
- `Brainiac` is the local memory/retrieval backend.
- `Jarvis` is the default operator that talks to Brainiac.
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

This repository now has the first read-only CLI inventory command over one Obsidian-style vault.

```bash
PYTHONPATH=src python3 -m brainiac scan --vault-root /path/to/obsidian-vault
```

`config/vault.yml` is local-only and ignored by git. On first run Brainiac creates it from `config/vault.example.yml`; set your local `vault.root` there or pass `--vault-root` for one-off scans. If `vault.root` is empty and the command is run interactively, Brainiac asks for the Obsidian vault path and optional folders to ignore. Extra ignores can also be passed with repeated `--exclude` flags. The command scans source formats from the vault config without mutating source files, writes a disposable SQLite index to `memory/index/brainiac.sqlite`, and writes an inventory report to `memory/generated/reports/inventory.md`.

The read-only retrieval and routing commands use the existing index:

```bash
PYTHONPATH=src python3 -m brainiac search "query"
PYTHONPATH=src python3 -m brainiac inspect path/to/note.md
PYTHONPATH=src python3 -m brainiac read path/to/note.md --section "Heading"
PYTHONPATH=src python3 -m brainiac related path/to/note.md
PYTHONPATH=src python3 -m brainiac route --file /path/to/draft.md
PYTHONPATH=src python3 -m brainiac find-duplicates --file /path/to/draft.md
PYTHONPATH=src python3 -m brainiac structure
```

`route` and `find-duplicates` are dry-run helpers. They suggest destinations, likely overlaps, and safe note/link names, but they do not write to the vault.
`structure` analyzes configured vault roles and profiles, then reports unconfigured areas/projects/resources that may need routing coverage.

See:

- [AGENTS.md](AGENTS.md)
- [docs/context-brief.md](docs/context-brief.md)
- [docs/concept.md](docs/concept.md)
- [docs/development-plan.md](docs/development-plan.md)
- [docs/phase-4-structure-notes.md](docs/phase-4-structure-notes.md)
- [docs/write-log-format.md](docs/write-log-format.md)
- [docs/source-takeaways.md](docs/source-takeaways.md)
- [docs/operator-context.md](docs/operator-context.md)
- [operator.md](operator.md)

## Two Contexts

Brainiac has two distinct operating contexts:

- `Development context`: build Brainiac itself. Read `AGENTS.md`, `README.md`, `docs/context-brief.md`, `docs/concept.md`, and `docs/development-plan.md`.
- `Operator context`: use Brainiac with a vault. Read `operator.md`, `docs/operator-context.md`, and the files in `config/`.
