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

Then update the state without completing setup:

```yaml
status: in_progress
current_step: obsidian_tasks
last_note: "Personal context collected. Enable the required Obsidian Tasks plugin."
```

### `obsidian_tasks`

Tasks is required. Explain that it is a third-party community plugin and must
be installed and enabled by the user in Obsidian:

1. Open **Settings → Community plugins**.
2. Enable community plugins if Obsidian shows Restricted Mode.
3. Browse, install, and enable **Tasks**.

Do not install a plugin or change Obsidian settings without explicit user
approval. After the user completes the UI step, verify it read-only by checking
that the vault has `.obsidian/plugins/obsidian-tasks-plugin/manifest.json` with
plugin id `obsidian-tasks-plugin`, and that
`.obsidian/community-plugins.json` lists the same id as enabled. If either
condition fails, keep `current_step: obsidian_tasks` and explain the missing
condition. On success, write:

```yaml
status: complete
current_step: complete
last_note: "Personal context collected and Obsidian Tasks enabled."
```

New managed vaults already contain a `TODO.md` quick-capture dashboard. Add
new tasks under `## Inbox`; its Tasks query renders other open tasks live.
Existing vaults receive this dashboard only through the versioned upgrade
flow, with an explicit review and backup.

### Missing Brainiac Installation

If `config/brainiac.yml` is missing, ask whether the user wants a new managed vault. For a new vault, run:

```bash
PYTHONPATH=src python3 -m brainiac init --vault-root /path/to/new-vault
```

`init` creates the PARA folders, local CLI config, personal-context scaffold, and state files. It does not migrate an existing vault layout.
