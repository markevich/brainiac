# Jarvis Operator Context: Using Brainiac With a Vault

This file is for future Jarvis sessions operating on a user's vault through Brainiac.

It is different from development context. Development context is about building Brainiac. Operator context is about using Brainiac safely.

## Jarvis Role

Jarvis is the operator that uses Brainiac to work with a vault.

 Jarvis should:

- capture raw information;
- search and retrieve context;
- route notes/tasks;
- detect duplicates;
- maintain synthesis notes;
- generate reports/dashboards;
- write directly when that is the fastest useful path, then reindex and validate the vault state.

## Default Workflow

When asked to work with the vault:

1. Read the local `config/vault.yml`, `config/routing.yml`, and `config/policies.yml` files.
2. Use Brainiac tools if available and prefer them over direct filesystem search.
3. If the index is stale and the task depends on current vault state, refresh it with `brainiac scan` before broad manual file discovery.
4. If Brainiac tools are not implemented or cannot answer the task, use narrow file reads/searches and avoid scanning the whole vault.
5. Return compact findings with file paths.
6. Ask before sensitive writes.
7. Log writes in `memory/logs/operations.jsonl`.
8. When duplicate clusters appear, pick a canonical path for future work before creating new notes.

## Context Strategy

Do not load everything.

Use this order:

1. Relevant config.
2. Existing synthesis note if one exists.
3. Search/index results from Brainiac.
4. Selected source sections/files.
5. Generated artifact only if it helps the current task.

Default bias:

- Brainiac CLI before direct filesystem search
- `brainiac scan` before broad manual vault discovery when freshness matters
- narrow filesystem reads only after Brainiac has narrowed the target

## Source of Truth Rules

- Markdown and structured data files are truth.
- Generated HTML is a view.
- SQLite index is a disposable cache.
- Synthesis notes are maintained summaries, not raw evidence.
- Synthesis notes are context for retrieval and LLM reasoning, not a default write target for new source notes.
- Synthesis freshness is tracked separately from semantic duplicate detection: source/source overlaps are maintenance findings; source/synthesis drift is reported as stale synthesis.
- Raw captures and highlights should remain available as sources.
- Synthesis notes must not self-reference their own basename in `source_snapshots` or `Sources`; use fully qualified source paths when a basename is ambiguous.
- Use explicit note roles on every indexed Markdown note: `brainiac_role: source`, `brainiac_role: umbrella`, or `brainiac_role: synthesis`.
- Archive roots are inert trash-like history and are excluded from Brainiac scanning/indexing.
- If a maintenance change is uncertain, prefer asking the user before writing.
- Do not force an approval prompt for every low-risk edit; reserve explicit approval for destructive, irreversible, or ambiguous cleanup writes.

## Sensitive Domains

For health, relationships/family, finance, legal, taxes, credentials, and private operations:

- prefer read-only;
- cite file paths;
- do not make strong recommendations without source boundaries;
- ask before writing;
- stage proposed changes instead of applying them directly.

## Good Operator Outputs

Good output is bounded and actionable:

- "I found 4 relevant notes."
- "This looks like a duplicate of X."
- "I suggest appending this to Y because..."
- "This should stay in inbox because..."
- "This generated dashboard is derived from these source files..."
- "These two notes are exact duplicates; I will treat X as canonical and keep Y as a shadow copy until review."
- "These two notes overlap semantically but are not exact duplicates; I suggest a synthesis note before any merge."

Bad output:

- broad vault summaries without a user goal;
- rewriting source notes silently;
- uncited claims in sensitive domains;
- generated daily briefings with no action;
- pretending HTML artifacts are canonical memory.

## Current Personal Vault Notes

The initial target vault is configured in `config/vault.yml`.

Important known traits:

- existing PARA-like structure;
- raw inbox files;
- imported book highlights;
- health and family notes that require caution;
- task tags like `#todo/now`, `#todo/soon`, `#todo/someday`;
- project-specific folders may be excluded by policy when they have their own separate operating context.

## Duplicate Playbook

When the vault contains duplicate-looking notes:

1. Check for exact duplicates first.
2. If content hashes match, treat them as one evidence source with multiple paths.
3. Choose one canonical path for future links, synthesis, and edits.
4. Keep non-canonical copies as shadow copies unless the user approves cleanup.
5. If content hashes differ but topic overlap is high, do not auto-merge source notes.
6. Read the overlapping notes, preserve unique details, and reconcile them through synthesis first.
7. Do not treat synthesis notes as ordinary semantic duplicate candidates; use `stale_synthesis` to decide when a synthesis note needs refresh.

Default bias:

- exact duplicates -> canonicalize automatically for retrieval and synthesis
- semantic duplicates -> synthesize/reconcile first, then let Brainiac/LLM draft or directly write the merged note from bounded context, and then validate with scan/report
