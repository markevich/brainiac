# Brainiac Setup Wizard

Run this only when `.state/setup.yml` is not `complete`.

## Resume Rules

- Read `.state/setup.yml` and resume from `current_step`.
- Do not restart setup because `brainiac_me.md` already exists.
- Update the state after each completed step.
- Set `status: complete` only after all required setup steps succeed.

## Steps

### `personal_context`

Ask for the user's preferred language and any useful personal context: domains, aliases, local projects, and working patterns. Write it to `brainiac_me.md`.

Then write:

```yaml
status: complete
current_step: complete
last_note: "Personal context collected."
```

### Missing Brainiac Installation

If `config/brainiac.yml` is missing, ask whether the user wants a new managed vault. For a new vault, run:

```bash
PYTHONPATH=src python3 -m brainiac init --vault-root /path/to/new-vault
```

`init` creates the PARA folders, local CLI config, personal-context scaffold, and state files. It does not migrate an existing vault layout.
