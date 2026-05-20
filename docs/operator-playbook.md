# Brainiac Operator Playbook

This playbook is the procedural startup and operating guide for Jarvis using Brainiac on a live vault.

Use it in operator context, not when developing Brainiac itself.

## Startup Order

When a new chat starts and the task is about operating on a vault:

1. Read the local `config/vault.yml`, `config/routing.yml`, and `config/policies.yml` files.
2. Read `operator.md`, `docs/operator-context.md`, and this playbook.
3. Run `brainiac index info`.
4. Run `brainiac index info --check-filesystem` by default for a new operator chat.
5. If the task clearly does not depend on current vault state, this filesystem drift check may be skipped.
6. Only run `brainiac scan` when:
   - the index is missing;
   - filesystem drift is non-trivial;
   - the user explicitly asks for reindexing;
   - a workflow depends on newly changed files not present in the current index.

Default bias:

- prefer bounded index tools over filesystem reads
- prefer Brainiac CLI over direct filesystem search for discovery and routing
- prefer `index info` before `scan`
- prefer `index info --check-filesystem` near the start of a new operator chat
- prefer `scan` before broad manual search

## Default Workflow

For most operator tasks, use this order:

1. `brainiac index info`
2. `brainiac index info --check-filesystem`
3. `brainiac search` or `brainiac inspect`
4. if a synthesis note exists, inspect it before reading raw notes
5. `brainiac related` for neighborhood context
6. `brainiac read` only for the selected notes
7. before any write-like proposal:
   - inspect duplicates/canonical path
   - inspect sensitivity/policy
   - prefer synthesis or dry-run output before source mutation

## Indexing Rules

Use `brainiac scan` like a cache maintenance operation, not a reflex.

Use `brainiac scan`:

- when the index is missing;
- when `index info --check-filesystem` shows real drift;
- after bulk note creation, moves, or deletes;
- before duplicate resolution or synthesis refresh that depends on latest content.

Use `brainiac scan --full-rebuild` only when:

- schema compatibility changed;
- the index looks corrupted or inconsistent;
- debugging requires a clean rebuild;
- the user explicitly requests a rebuild.

## Retrieval Rules

Filesystem fallback rule:

- do not start with `rg`, `find`, or broad raw-file content search across the vault when Brainiac CLI can answer the question after an index check or scan
- use direct filesystem inspection only after Brainiac has narrowed the target path, or when debugging/index coverage makes Brainiac insufficient for the task

`brainiac search`

- use for topic discovery and lexical lookup
- use before broad file reading

`brainiac inspect`

- use to understand one note's metadata, links, tasks, synthesis references, exact duplicates, and canonical path

`brainiac related`

- use after `inspect` when a note needs local context
- trust explicit links/backlinks more than same-folder proximity
- treat weak lexical neighbors as optional context, not evidence

`brainiac read`

- use only after narrowing candidates
- prefer one file or one section at a time

## Synthesis Rules

Synthesis is derived memory, not source truth.
Synthesis is valid operator context, but not a default write target for new source notes.

Use `brainiac synthesis suggest` when:

- a topic is important enough to preserve conclusions over time;
- multiple raw notes overlap and need reconciliation;
- exact or semantic duplicates need to be understood before source-note cleanup.

Use `brainiac synthesis stale` when:

- synthesis notes already exist;
- the user wants to refresh conclusions after source changes;
- maintenance work is focused on keeping derived memory current.

Freshness rule:

- if a source note changes after a synthesis snapshot was recorded, the synthesis note becomes stale;
- stale synthesis is reported separately from semantic duplicates;
- semantic duplicate checks should compare source notes against source notes, not source notes against derived synthesis notes.

Default synthesis workflow:

1. `brainiac synthesis suggest <topic-or-path>`
2. keep strong source notes as the main evidence set
3. treat body-only lexical matches as weak context
4. read only selected source notes or sections
5. write or update synthesis only through explicit review/apply workflow
6. avoid self-referential `source_snapshots` or basename-only `Sources` entries in generated synthesis notes when they collide with another indexed note basename
7. prefer explicit `brainiac_role: source` on ordinary notes and `brainiac_role: synthesis` frontmatter on generated synthesis notes

## Duplicate Rules

Treat duplicates in two classes.

### Exact duplicates

Definition:

- same content hash, different paths

Default handling:

- Brainiac should choose a canonical path automatically for retrieval, relatedness, and synthesis
- do not use all exact duplicate copies as separate synthesis evidence
- do not silently delete shadow copies
- prefer fixing future links and writes to point at the canonical note
- current implemented behavior is diagnostic and preference-setting first; if you want to repair the vault, prefer direct LLM edits followed by a fresh scan/report pass

### Semantic duplicates

Definition:

- different content, but overlapping topic or intent

Default handling:

- do not auto-merge source notes on first detection
- inspect both notes
- preserve unique details from both
- synthesize first
- treat synthesis/source drift as stale synthesis, not as an ordinary semantic duplicate
- only then draft or directly write a merged note from bounded context, then validate the vault with scan/report
- ignore archive roots entirely; they are outside Brainiac's normal scan/index boundary
- surface notes that should have an explicit `brainiac_role` marker but do not

## Canonicalization Heuristics

When Brainiac must choose one canonical note among exact duplicates, prefer:

1. non-generated, non-queue notes
2. non-inbox notes for durable knowledge
3. notes with stronger graph connectivity
5. more recently maintained notes

This is a retrieval/write preference, not an automatic deletion rule.

## Write Rules

Before proposing or applying writes:

1. confirm the target path is canonical
2. check whether the path is sensitive
3. check whether synthesis should be updated first
4. prefer dry-run or staged output when uncertainty remains
5. if the target, outcome, or cleanup scope is unclear, ask the user for approval before writing

Do not:

- create new ambiguous basename duplicates
- merge or delete source notes silently
- rewrite sensitive notes without explicit approval

Approval bias:

- if the change is low-risk, deterministic, and reversible, keep the write path lightweight
- if the change is destructive, cross-note, or cleanup-oriented, ask first
- if the maintenance finding is ambiguous, treat user approval as the default

## Maintenance Workflows

Use Brainiac to detect and then repair vault defects.

Current defect classes:

- filesystem drift versus index
- missing wikilinks
- ambiguous wikilinks
- exact duplicate clusters
- semantic duplicate clusters
- stale synthesis notes
- unconfigured structure profiles

Preferred order for maintenance:

1. refresh or validate the index
2. inspect duplicate/canonical clusters
3. refresh or create synthesis for overlapping topics
4. only then propose source-note retirement, cleanup, or link rewrites

Important distinction:

- diagnostics and canonical preferences should exist before cleanup tooling
- a vault can be understood correctly before it can be rewritten safely

## Command Cookbook

```bash
PYTHONPATH=src python3 -m brainiac index info
PYTHONPATH=src python3 -m brainiac index info --check-filesystem
PYTHONPATH=src python3 -m brainiac scan
PYTHONPATH=src python3 -m brainiac scan --full-rebuild
PYTHONPATH=src python3 -m brainiac search "query"
PYTHONPATH=src python3 -m brainiac inspect path/to/note.md
PYTHONPATH=src python3 -m brainiac read path/to/note.md --section "Heading"
PYTHONPATH=src python3 -m brainiac related path/to/note.md
PYTHONPATH=src python3 -m brainiac route --file /path/to/draft.md
PYTHONPATH=src python3 -m brainiac find-duplicates --file /path/to/draft.md
PYTHONPATH=src python3 -m brainiac duplicates list
PYTHONPATH=src python3 -m brainiac duplicates inspect <path-or-group>
PYTHONPATH=src python3 -m brainiac structure
PYTHONPATH=src python3 -m brainiac synthesis list
PYTHONPATH=src python3 -m brainiac synthesis inspect "topic"
PYTHONPATH=src python3 -m brainiac synthesis stale
PYTHONPATH=src python3 -m brainiac synthesis suggest "topic-or-path"
PYTHONPATH=src python3 -m brainiac maintenance report
```

## Current Biases

Use these biases until more advanced workflows exist:

- exact duplicates: canonicalize automatically in retrieval and synthesis
- semantic duplicates: synthesize/reconcile first, then let Brainiac/LLM draft or directly write the merged note from bounded context, and then validate with scan/report
- inbox and todo notes: good context, weak canonical memory
- archive roots: outside the Brainiac index
- synthesis notes: first context layer when they exist
