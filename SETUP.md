# Brainiac Setup

Use this when installing Brainiac for a new person.

Brainiac keeps local machine paths in gitignored files:

- `config/vault.yml`
- `config/routing.yml`

The tracked `*.example.yml` files are templates only.

## LLM Flow

When an LLM helps a user onboard Brainiac, it should do this in order:

1. Ask for the local vault path.
2. Ask whether the vault should follow the standard PARA roots.
3. If yes, default to `Inbox/`, `Projects/`, `Areas/`, `Resources/`, and `Archive/`.
4. Ask whether the vault should also contain `Brainiac/memory/synthesis/`, `Brainiac/memory/queue/`, and `Brainiac/memory/generated/`.
5. Ask which folders should be ignored during scan.
6. Fill `config/vault.yml`.
7. Fill `config/routing.yml`.
8. If the user wants it, create the missing folders in the vault manually.
9. Run `PYTHONPATH=src python3 -m brainiac scan`.

The LLM should not guess absolute machine paths. It should ask for them.

## Recommended PARA Defaults

If you standardize on PARA, use:

- `Inbox/`
- `Projects/`
- `Areas/`
- `Resources/`
- `Archive/`
- `Brainiac/memory/synthesis/`
- `Brainiac/memory/queue/`
- `Brainiac/memory/generated/`

## What To Fill In `config/vault.yml`

Required:

- `vault.root`

Usually fill too:

- `vault.name`
- `exclude`

Normally leave as-is:

- `source_formats`
- `generated_paths`
- `index.path`

Minimal example:

```yml
vault:
  name: "My vault"
  root: "/absolute/path/to/my/vault"

exclude:
  - ".obsidian/"
  - ".trash/"
```

## What To Fill In `config/routing.yml`

Required for PARA onboarding:

- `inbox.default`
- `projects.root`
- `areas.default`
- `resources.default`
- `archive_roots`

Usually also fill:

- `inbox_roots`
- `project_roots`
- `area_roots`
- `resource_roots`
- `synthesis.root` and `synthesis_roots`
- `queue.root` and `queue_roots`
- `generated.root` and `generated_roots`

Minimal example:

```yml
inbox:
  default: "Inbox/"

projects:
  root: "Projects/"

areas:
  default: "Areas/"

resources:
  default: "Resources/"

inbox_roots:
  - "Inbox/"

project_roots:
  - "Projects/"

area_roots:
  - "Areas/"

resource_roots:
  - "Resources/"

archive_roots:
  - "Archive/"
```

## After Setup

Run:

```bash
PYTHONPATH=src python3 -m brainiac scan
```

That builds the disposable index for the configured vault.
