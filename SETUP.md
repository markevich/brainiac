# Brainiac Setup

Use this when installing Brainiac for a new person.

Brainiac keeps local machine paths in gitignored files:

- `config/vault.yml`

`brainiac init` creates this local config for a new managed vault.

## LLM Flow

When an LLM helps a user onboard Brainiac, it should do this in order:

1. Ask whether this is a new vault or an existing vault.
2. For a new vault, run `brainiac init --vault-root /path/to/new-vault`. It creates the required PARA roots and local `vault.yml`.
3. For an existing vault, do not create or move files. A future migration planner will produce a dry-run plan; until then, use bounded read-only tools only after an explicit PARA migration decision.
4. Run `PYTHONPATH=src python3 -m brainiac scan` only after the user has an explicit config.

The LLM should not guess absolute machine paths. It should ask for them.

## Recommended PARA Defaults

Every new Brainiac-managed vault uses:

- `Inbox/`
- `Projects/`
- `Areas/`
- `Resources/`
- `Archive/`

## What To Fill In `config/vault.yml`

Required:

- `vault.root`

Usually fill too:

- `vault.name`
- `exclude`

Normally leave as-is:

- `source_formats`
- `index.path`

Minimal example:

```yml
vault:
  version: 1
  name: "My vault"
  root: "/absolute/path/to/my/vault"
  layout: para

exclude:
  - ".obsidian/"
  - ".trash/"
```

## After Setup

Run:

```bash
PYTHONPATH=src python3 -m brainiac scan
```

That builds the disposable index for the configured vault.
