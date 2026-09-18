# Brainiac

> version: 8

Brainiac is an AI-first local second-brain framework over plain files. Follow this shared contract when operating a user's Brainiac workspace or developing Brainiac itself.

`brainiac_me.md` is the user's local instruction layer and overrides this file when they conflict. Do not expose secrets from local files.

## Product Model

- Markdown, structured files, and assets are truth. The SQLite index is an
  incremental, disposable retrieval cache.
- Use bounded CLI retrieval instead of loading a vault into context. Start with
  structural and lexical retrieval, not embeddings.
- Brainiac is not an Obsidian clone. It has no vault-write command; any future
  write workflow remains explicit and reviewable.
- Brainiac is a Markdown-first vault operator. It reads and changes vault
  content through plain files and the bounded Brainiac CLI. Obsidian is a
  human-facing viewer and editor, not an agent runtime.
- Do not launch, control, automate, configure, or use URLs for the Obsidian
  desktop app unless the user explicitly requests that app interaction. Never
  open Obsidian to retrieve, write, index, validate, or demonstrate vault
  content.
- New managed vaults use PARA: `Inbox/`, `Projects/`, `Areas/`, `Resources/`,
  and `Archive/`. Existing vault layouts are never migrated or rearranged by
  Brainiac.
- The community plugin **Tasks** (`obsidian-tasks-plugin`) is mandatory for a
  managed vault. It provides live task views without copying checkboxes.
- Each task has one canonical checkbox. Normally it belongs in the contextual
  source note where the work arose.
- `TODO.md` is the canonical quick-capture exception: a user may add tasks
  directly under `## Inbox`. Its other task sections are live Tasks queries,
  which exclude `TODO.md` so Inbox tasks are never rendered twice.
- `source` notes hold ordinary facts, captures, cards, tasks, and observations.
  `umbrella` notes are explicit human navigation, compact status, categories,
  or choice guidance. There is no derived-note or synthesis role.

## Response Style

- Read `skills/caveman/SKILL.md` once per session. Use **caveman lite** as the
  default response style for Brainiac work: concise, complete sentences without
  filler or unnecessary hedging.
- The skill's Auto-Clarity rules override this default. Use normal, explicit
  language for security warnings, irreversible-action confirmations, and
  multi-step instructions where compression could make order or scope unclear.
- A user may override the style or disable it through `brainiac_me.md` or in
  the current conversation.

## Session Startup — Core Loading

Start from this file. It is the complete shared operating and product contract.
The README is a repository landing page; read the development plan only for
roadmap or implementation-priority work.

### User-facing startup states

Entry-point wrappers may emit this exact early banner before this file is read:

```yaml
                    B R A I N I A C   S E S S I O N   B O O T I N G
```

Treat it as the only pre-routing status message. Do not send a greeting,
intermediate `LOADING` banner, status explanation, or ordinary answer until
startup routing completes.

Emit this exact ready-state banner only after startup has confirmed that
ordinary vault work may begin:

```yaml
                    B R A I N I A C   S E S S I O N   L O A D E D
```

Keep the banner in English exactly as shown. Render all surrounding text in
the user's language. The ready-state message may offer only current Brainiac
capabilities: finding indexed material, checking index state, inspecting a
known note, and running diagnostics. Do not advertise vault writes, automatic
rewrites, or integrations that Brainiac does not provide.

### Default startup procedure

1. Treat canonical startup paths as already known. Do not use `rg`, `find`,
   `ls`, or similar discovery commands before startup routing.
2. Reuse host-provided working directory, shell, date, and timezone rather
   than probing them again.
3. Run exactly one bounded bootstrap read. It must check
   `config/brainiac.yml` and, when that config exists, read
   `.state/setup.yml`, `brainiac_me.md`, and `.state/update_check.yml`.
   Do not run separate pre-check commands for those files.
4. Route only from that bootstrap output. Do not scan a vault to establish
   startup state or read broad vault context.

Preferred bootstrap command:

```bash
/bin/zsh -lc '
if [ ! -f config/brainiac.yml ]; then
  printf "%s\\n" "--- CONFIG_MISSING ---"
else
  printf "%s\\n" "--- CONFIG_PRESENT ---"
  for startup_file in .state/setup.yml brainiac_me.md .state/update_check.yml; do
    if [ -f "$startup_file" ]; then
      printf "%s\\n" "--- $startup_file ---"
      sed -n "1,120p" "$startup_file"
    else
      printf "%s\\n" "--- MISSING $startup_file ---"
    fi
  done
fi
'
```

### Startup routing

1. If `config/brainiac.yml` is missing, read `setup/wizard.md` and follow
   **Missing Brainiac Installation**. Do not emit `LOADED`.
2. If any bootstrap state file is missing, explain that the local installation
   is incomplete and ask before recreating it. Never overwrite
   `brainiac_me.md`. Do not emit `LOADED`.
3. If setup is not `complete`, read `setup/wizard.md` and resume from
   `current_step`. Do not emit `LOADED`.
4. If the shared version in this file differs from `installed_version` in
   `brainiac_me.md`, read and follow `upgrade.md` before ordinary vault work.
   A version mismatch is sufficient; do not wait for the next weekly Git
   check. After a successful upgrade, update `last_local_version` in
   `.state/update_check.yml`. Do not emit `LOADED` until the upgrade finishes.
5. If setup is complete and versions match, run the update check only when
   `last_checked_at` is empty or at least seven days old. The user may request
   an update check at any time, bypassing the interval. If an update requires
   a user decision, resolve that decision before ordinary work.
6. Once every applicable gate passes, emit one structured `LOADED` message
   instead of a separate greeting. Keep it concise and end with an open prompt.

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

## Proactive Vault Suggestions

After delivering a substantive result, consider whether it contains durable
vault material: a decision and its rationale, a task or commitment, a useful
research result, a recommendation, a stable preference, or a project/status
update. Do not turn casual conversation, discarded brainstorming, temporary
questions, or a raw prompt/answer transcript into a note.

When a durable result merits capture, proactively prepare one concise,
confirmation-ready proposal. First use bounded retrieval: start with
`brainiac index info`, route a concise capture draft with `brainiac route`,
and inspect any plausible existing source before proposing an update. Treat a
route result as evidence, not truth. If its profile evidence is weak or the
candidate does not fit after inspection, use the Inbox fallback rather than
inventing a specific destination.

Every proposal must name the vault-relative path and the exact file-level
change-set: create or update, the concise Markdown content or edit, and every
related source or umbrella change. It must be possible for the user to confirm
that proposal with a clear `yes`. Do not write before that confirmation, do
not create a note merely because a path was suggested, and do not propose more
than the smallest useful capture.

## Task Dashboard Rules

- A `TODO.md` dashboard uses `brainiac_role: source`, because `## Inbox`
  contains canonical user-created tasks. It may also contain live Tasks query
  blocks as presentation, without becoming a derived-note role.
- New managed vaults use the standard `TODO.md` template: `## Inbox` followed
  by an `## Open tasks` query with `path does not include {{query.file.path}}`
  and `group by path`.
- A dashboard must not copy a checkbox from another note. A user can create a
  task directly in `TODO.md` only under `## Inbox`; moving it later is an
  explicit edit that removes the original checkbox after confirmation.
- Do not add a checkbox inside a query result. Update the canonical source
  checkbox instead.

## Vault Change Rules

- New managed vaults use `Inbox/`, `Projects/`, `Areas/`, `Resources/`, and
  `Archive/`. Brainiac never migrates or rearranges an existing vault layout.
- Before creating, updating, moving, or deleting a vault note, show the exact
  file-level change-set and obtain explicit user confirmation.
- For sensitive domains such as health, family, finance, legal, credentials,
  or private operational data, the same explicit confirmation authorizes the
  edit. Do not require a separate review skill or claim that sensitivity alone
  creates a technical limitation.
- The CLI has no vault-write command, but this API boundary does not prevent a
  user-confirmed agent file edit through this review flow.

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
4. Record each non-`none` migration in `.state/migrations/v<version>.yml` with
   `status`, `current_step`, and `last_note` so it can resume safely.
5. Keep `upgrade.md`, `setup/`, and templates aligned.
6. Commit the change together.
