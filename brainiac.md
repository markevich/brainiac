# Brainiac

> version: 2

Brainiac is an AI-first local second-brain framework over plain files. Follow this shared contract when operating a user's Brainiac workspace or developing Brainiac itself.

`brainiac_me.md` is the user's local instruction layer and overrides this file when they conflict. Do not expose secrets from local files.

## Product Model

- Markdown, structured files, and assets are truth. The SQLite index is an
  incremental, disposable retrieval cache.
- Use bounded CLI retrieval instead of loading a vault into context. Start with
  structural and lexical retrieval, not embeddings.
- Brainiac is not an Obsidian clone. It has no vault-write command; any future
  write workflow remains explicit and reviewable.
- New managed vaults use PARA: `Inbox/`, `Projects/`, `Areas/`, `Resources/`,
  and `Archive/`. Existing vault layouts are never migrated or rearranged by
  Brainiac.
- `source` notes hold ordinary facts, captures, cards, tasks, and observations.
  `umbrella` notes are explicit human navigation, compact status, categories,
  or choice guidance. There is no derived-note or synthesis role.

## Session Startup

Start from this file. It is the complete shared operating and product contract.
The README is a repository landing page; read the development plan only for
roadmap or implementation-priority work.

1. Check whether `config/brainiac.yml` exists.
2. If it is missing, read `setup/wizard.md` and follow **Missing Brainiac
   Installation**. Do not scan a vault just to establish startup state.
3. If it exists, read `.state/setup.yml`, `brainiac_me.md`, and
   `.state/update_check.yml` in one bounded bootstrap pass.
4. If one of those bootstrap files is missing, explain that the local
   installation is incomplete and ask before recreating any file. Never
   overwrite `brainiac_me.md`.

If setup is not `complete`, read `setup/wizard.md` and resume from `current_step`. Do not scan the vault just to establish startup state.

If setup is complete but the shared `version` in this file differs from
`installed_version` in `brainiac_me.md`, read and follow `upgrade.md` before
ordinary vault work. A version mismatch is sufficient; do not wait for the
next weekly Git check. After a successful upgrade, update `last_local_version`
in `.state/update_check.yml`.

If setup is complete and versions match, run the update check only when
`last_checked_at` is empty or at least seven days old. The user may request an
update check at any time, bypassing the interval.

## Update Check

Brainiac is always installed from a Git checkout. When an update check is due:

1. Run `git fetch --quiet` in the Brainiac workspace.
2. Compare `HEAD` with `@{u}`.
3. Record the result, `last_checked_at`, and the current local contract
   version in `.state/update_check.yml`, even if the check fails.
4. If upstream is ahead, read the upstream `brainiac.md` with Git, show the
   local and upstream versions, and ask whether to update.
5. Never run `git pull` without the user's approval.

After approval, use `git pull --ff-only`, re-read `brainiac.md`, and compare
its version with `installed_version` in `brainiac_me.md`. If they differ, read
and follow `upgrade.md`.

## CLI and Retrieval Loop

1. Use `config/brainiac.yml` as the sole CLI configuration for the current
   vault and its index. Do not override its vault root or index path at runtime.
2. Begin ordinary vault work with `brainiac index info`; add
   `--check-filesystem` only when freshness matters.
3. Scan only when the index is missing, drift matters to the task, the user
   explicitly asks, or a confirmed note change needs to refresh retrieval.
   Do not read the vault broadly as a substitute for bounded retrieval.
4. Retrieve in order: `search`, `inspect` or `related`, then `read` only the
   necessary note or section.
5. If lexical search is empty or weak, try one bounded expansion first: a
   translation, close synonym, category, or location term. Treat a repeated
   miss as product evidence; do not invent a feature from one miss.
6. Use `maintenance report` for diagnostics. Preserve uncertain duplicate or
   semantic-overlap candidates; do not silently merge or delete notes.

Vault files are truth and the SQLite index is disposable. The current CLI has
no vault-write command; route suggestions are dry-run only.

## Vault Change Rules

- New managed vaults use `Inbox/`, `Projects/`, `Areas/`, `Resources/`, and
  `Archive/`. Brainiac never migrates or rearranges an existing vault layout.
- Do not create, update, move, or delete vault notes without the user's
  confirmation. Sensitive domains remain read-only unless the user explicitly
  authorizes the change.

## Source and Umbrella Rules

- Every new ordinary note is a `source` and carries
  `brainiac_role: source` in frontmatter. An `umbrella` explicitly carries
  `brainiac_role: umbrella`; these are the only valid roles.
- Before creating a source, use bounded search to decide whether an existing
  umbrella covers the same navigation or choice problem. Before materially
  updating a source, inspect its existing umbrella backlinks. Include every
  necessary source and umbrella change in one proposed change-set.
- If no suitable umbrella exists, create the source normally. Propose a new
  umbrella only when a person needs a compact map, status view, categories, or
  choice guidance. Related notes, a shared folder, common terms, or note count
  alone are not enough.
- Do not apply any source or umbrella change until the user confirms that
  change-set. After all confirmed note edits, run one `brainiac scan`, then
  `brainiac inspect <path>`. `Umbrella backlinks` are indexed links from notes
  explicitly marked `brainiac_role: umbrella`.
- For every umbrella backlink, propose an umbrella update when the source
  changed its navigation, categories, status, ratings, or choice guidance. If
  none of those changed, leave the umbrella untouched and say why. If the
  inspection reveals an umbrella change absent from the confirmed change-set,
  ask for a second confirmation before editing it, then scan once more.
- If no umbrella backlink exists after the scan, use bounded search only when
  there is still a clear navigation problem. Never create an umbrella merely
  to satisfy a maintenance rule.
- `maintenance report` diagnoses missing or invalid role markers. Fix a role
  marker deliberately; do not infer an umbrella from a note's title alone.

## Versioning Rules

When changing this shared installation flow:

1. Bump `version` in this file.
2. Add a matching entry and `### Migration` section to `changelog/` through `CHANGELOG.md`.
3. Make every migration idempotent: it verifies its target state before
   changing files, safely skips completed work, and validates its final state.
4. Keep `upgrade.md`, `setup/`, and templates aligned.
5. Commit the change together.
