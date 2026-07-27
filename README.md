# Brainiac

AI-first local second-brain framework over plain files.

```text
vault files -> incremental SQLite index -> bounded CLI tools -> Jarvis
```

Markdown and structured files are truth. The index is an incremental, rebuildable cache. Brainiac is not an Obsidian clone.

## Vault layout

New Brainiac-managed vaults use PARA: `Inbox/`, `Projects/`, `Areas/`, `Resources/`, and `Archive/`. The disposable SQLite index stays in the local Brainiac workspace, outside the vault. Existing vaults are migrated only through an explicit, reviewed migration plan; Brainiac never rearranges them automatically.

## Note roles

- `source` is the default role for new notes.
- `umbrella` is an explicit navigation note that links sources, groups them, and may contain compact working rules.

After a material source update, inspect its umbrella backlinks and propose an umbrella update only if the change affects navigation, categories, status, ratings, or selection guidance.

## Commands

```bash
PYTHONPATH=src python3 -m brainiac init --vault-root /path/to/new-vault
PYTHONPATH=src python3 -m brainiac scan --vault-root /path/to/vault
PYTHONPATH=src python3 -m brainiac index info --check-filesystem
PYTHONPATH=src python3 -m brainiac search "query"
PYTHONPATH=src python3 -m brainiac inspect path/to/note.md
PYTHONPATH=src python3 -m brainiac read path/to/note.md --section "Heading"
PYTHONPATH=src python3 -m brainiac related path/to/note.md
PYTHONPATH=src python3 -m brainiac route --file /path/to/draft.md
PYTHONPATH=src python3 -m brainiac find-duplicates --file /path/to/draft.md
PYTHONPATH=src python3 -m brainiac duplicates list
PYTHONPATH=src python3 -m brainiac maintenance report
PYTHONPATH=src python3 -m brainiac structure
```

See [AGENTS.md](AGENTS.md), [SETUP.md](SETUP.md), [docs/brainiac-intro.md](docs/brainiac-intro.md), and [operator.md](operator.md).
