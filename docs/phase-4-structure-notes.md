# Phase 4 Structure Notes

This note records the implementation details and validation state for the first Phase 4 slice.

## Scope Implemented

This first slice implemented a configurable role-based model. The product decision now is stricter: new Brainiac-managed vaults must use PARA. The configurable roots remain transitional compatibility for an existing vault until it is explicitly migrated.

Implemented command:

```bash
PYTHONPATH=src python3 -m brainiac structure
```

The command reads the existing SQLite index and `config/routing.yml`. It does not scan, write to the vault, or infer local paths from hardcoded defaults.

## Config Model

Role roots are configured in `config/routing.yml`:

```yaml
inbox_roots:
  - "0_Inbox/"

project_roots:
  - "1_Projects/"

area_roots:
  - "2_Areas/"

resource_roots:
  - "3_Resources/"
  - "ibooks-highlights/"

queue_roots:
  - "Brainiac/memory/queue/"

generated_roots:
  - "Brainiac/memory/generated/"
```

For a new Brainiac-managed vault, canonical roots are `Inbox/`, `Projects/`, `Areas/`, `Resources/`, and `Archive/`; `Brainiac/` is tool-owned. Alternative paths are compatibility configuration for an existing vault, not a new-vault option.

`stopwords` are also config-driven. They are only used to keep displayed top terms and profile signals cleaner; they do not mutate vault content.

## Structure Profiles

`brainiac structure` builds profiles for configured role roots:

- role;
- path;
- note count;
- file count;
- routing coverage status: `route-configured` or `route-missing`;
- sensitive flag;
- top tags;
- top terms;
- representative notes.

For roots that contain subfolders, profiles are built for first-level children. Flat resource collections, such as imported book highlights, are represented as one profile instead of one profile per file.

## Validation Results

Validated scenarios:

- Full test suite: `19 tests OK`.
- Compile check: `PYTHONPATH=src python3 -m compileall -q src tests`.
- Diff check: `git diff --check`.
- Current vault:
  - detects `2_Areas/3d print/` as `route-missing`;
  - detects `2_Areas/Вокал/` as `route-missing`;
  - marks configured sensitive areas from config;
  - treats `ibooks-highlights/` as one resource profile.
- Existing custom vaults remain readable through explicitly configured roots.
- New-vault PARA enforcement and migration planning are not implemented by this first slice.

## Remaining Work

The next useful step is to enforce PARA for new vaults and offer a dry-run migration plan for existing ones. After that, profiles can inform routing:

- rank area/project/resource profiles before choosing a destination;
- use profile signals for low-confidence and new-area suggestions;
- add optional aliases/domain hints as local overrides;
- add profile summaries and recent activity;
- avoid depending on manual multilingual keyword dictionaries as the main routing strategy.
