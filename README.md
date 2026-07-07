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

`config/vault.yml` and `config/routing.yml` are local-only and ignored by git. On first run Brainiac creates them from `config/vault.example.yml` and `config/routing.example.yml`; set your local vault root and local routing/profile mappings there, or pass overrides such as `--vault-root` or `--routing-config` for one-off runs. If `vault.root` is empty and the command is run interactively, `scan` asks for the Obsidian vault path and optional folders to ignore. Extra ignores can also be passed with repeated `--exclude` flags. See `SETUP.md` for the recommended manual onboarding flow and the LLM checklist for filling both configs under a PARA-style vault. The command scans source formats from the vault config without mutating source files, writes a disposable SQLite index to `memory/index/brainiac.sqlite`, and writes an inventory report to `memory/generated/reports/inventory.md`.

`scan` is incremental by default when a compatible index already exists for the same vault root. Brainiac still walks the vault tree to detect additions and deletions, but it only reparses changed Markdown files and then re-resolves wikilinks globally from indexed link rows. Use `--full-rebuild` when you intentionally want to discard reuse and rebuild the index from scratch.

The read-only retrieval and routing commands use the existing index:

```bash
PYTHONPATH=src python3 -m brainiac search "query"
PYTHONPATH=src python3 -m brainiac inspect path/to/note.md
PYTHONPATH=src python3 -m brainiac read path/to/note.md --section "Heading"
PYTHONPATH=src python3 -m brainiac related path/to/note.md
PYTHONPATH=src python3 -m brainiac index info
PYTHONPATH=src python3 -m brainiac index info --check-filesystem
PYTHONPATH=src python3 -m brainiac route --file /path/to/draft.md
PYTHONPATH=src python3 -m brainiac find-duplicates --file /path/to/draft.md
PYTHONPATH=src python3 -m brainiac duplicates list
PYTHONPATH=src python3 -m brainiac duplicates inspect <path-or-group>
PYTHONPATH=src python3 -m brainiac maintenance report
PYTHONPATH=src python3 -m brainiac structure
PYTHONPATH=src python3 -m brainiac synthesis list
PYTHONPATH=src python3 -m brainiac synthesis inspect "topic"
PYTHONPATH=src python3 -m brainiac synthesis stale
PYTHONPATH=src python3 -m brainiac synthesis suggest "topic"
```

`route` and `find-duplicates` are dry-run helpers. They suggest destinations, likely overlaps, and safe note/link names, but they do not write to the vault.
`duplicates list` and `duplicates inspect` are read-only maintenance diagnostics. They show exact duplicate clusters, the current canonical candidate, why that path wins, and separate semantic duplicate ideas from exact duplicate groups.
`maintenance report` is a read-only defect report layer. It currently aggregates meaningful empty directories, exact duplicate clusters, stale synthesis notes, missing wikilinks, ambiguous wikilinks, unconfigured structure profiles, and semantic duplicate candidates into one maintenance finding model, using ignore rules plus role/structure semantics.
The preferred maintenance loop is simpler: `maintenance report` or targeted inspection, LLM-authored edits, then `scan` and `report` again to validate the vault state.
When a maintenance change is uncertain, ask the user before writing; destructive or ambiguous cleanup should not be applied silently.
Brainiac now treats note roles explicitly: `source` is the default user-content role, `umbrella` is a master list/index note, and `synthesis` is derived memory. Configured archive roots are inert trash and are excluded from the index.
Every indexed Markdown note should carry an explicit `brainiac_role` marker. Maintenance flags notes missing one and suggests the likely role to add.
`structure` analyzes configured vault roles and profiles, then reports unconfigured areas/projects/resources that may need routing coverage.
`synthesis` commands treat synthesis notes as derived memory over raw sources. They list synthesis notes, inspect source references, report stale notes when source snapshots no longer match the current index, and dry-run draft synthesis notes without writing to the vault.

See:

- [AGENTS.md](AGENTS.md)
- [SETUP.md](SETUP.md)
- [docs/brainiac-intro.md](docs/brainiac-intro.md)
- [docs/context-brief.md](docs/context-brief.md)
- [docs/concept.md](docs/concept.md)
- [docs/development-plan.md](docs/development-plan.md)
- [docs/phase-4-structure-notes.md](docs/phase-4-structure-notes.md)
- [docs/synthesis-format.md](docs/synthesis-format.md)
- [docs/write-log-format.md](docs/write-log-format.md)
- [docs/source-takeaways.md](docs/source-takeaways.md)
- [docs/operator-context.md](docs/operator-context.md)
- [docs/operator-playbook.md](docs/operator-playbook.md)
- [operator.md](operator.md)

## Two Contexts

Brainiac has two distinct operating contexts:

- `Development context`: build Brainiac itself. Read `AGENTS.md`, `README.md`, `docs/brainiac-intro.md`, `docs/concept.md`, and `docs/development-plan.md`.
- `Operator context`: use Brainiac with a vault. Read `docs/brainiac-intro.md`, `operator.md`, `docs/operator-context.md`, `docs/operator-playbook.md`, and the files in `config/`.
