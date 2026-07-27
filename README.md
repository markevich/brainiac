# Brainiac

AI-first local second-brain framework over plain files.

```text
vault files -> incremental SQLite index -> bounded CLI tools -> Jarvis
```

Markdown and structured files are truth. The index is an incremental, rebuildable cache. Brainiac is not an Obsidian clone.

## Installation Layers

- `brainiac.md` is the tracked shared LLM contract and update flow.
- `brainiac_me.md` is the gitignored personal context and overrides shared instructions on conflicts.
- `config/brainiac.yml` is the gitignored CLI config for one vault.
- `.state/` contains resumable setup and weekly update-check state.

## Vault layout

New Brainiac-managed vaults use PARA: `Inbox/`, `Projects/`, `Areas/`, `Resources/`, and `Archive/`. The disposable SQLite index stays in the local Brainiac workspace, outside the vault. Brainiac never rearranges an existing vault layout.

## Note roles

- `source` is the default role for new notes.
- `umbrella` is an explicit navigation note that links sources, groups them, and may contain compact working rules.

After a material source update, inspect its umbrella backlinks and propose an umbrella update only if the change affects navigation, categories, status, ratings, or selection guidance.

## Commands

```bash
PYTHONPATH=src python3 -m brainiac init --vault-root /path/to/new-vault
PYTHONPATH=src python3 -m brainiac scan
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

Read [brainiac.md](brainiac.md) for the shared LLM product and operating
contract, and [SETUP.md](SETUP.md) for installation.
