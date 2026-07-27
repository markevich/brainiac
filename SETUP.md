# Brainiac Setup

Use this when installing Brainiac for a new person.

Brainiac separates shared instructions, local personal context, and CLI configuration:

- `brainiac.md` — tracked shared LLM contract.
- `brainiac_me.md` — gitignored personal context and installation version.
- `config/brainiac.yml` — gitignored CLI config for a vault.
- `.state/` — gitignored setup and update-check state.

`brainiac init` creates the local CLI config, personal-context scaffold, and
two state files for a new managed vault. The generated personal context starts
at the shared `brainiac.md` version.

## LLM Flow

When an LLM helps a user onboard Brainiac, it should do this in order:

1. Ask whether this is a new vault or an existing vault.
2. For a new vault, run `brainiac init --vault-root /path/to/new-vault`. It creates the PARA roots, `config/brainiac.yml`, `brainiac_me.md`, and `.state/`.
3. Resume `setup/wizard.md` through the shared startup flow in `brainiac.md` to fill personal context. `brainiac.md` is also the sole shared operator contract for later sessions.
4. Brainiac does not migrate an existing vault layout.
5. Run `PYTHONPATH=src python3 -m brainiac scan` after setup is complete.

The LLM should not guess absolute machine paths. It should ask for them.

## Recommended PARA Defaults

Every new Brainiac-managed vault uses:

- `Inbox/`
- `Projects/`
- `Areas/`
- `Resources/`
- `Archive/`

## What To Fill In `config/brainiac.yml`

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
brainiac:
  config_version: 1

vault:
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
