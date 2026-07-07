# Brainiac Intro

This file is the shortest accurate mental model for a new chat.

Read this before the playbook or roadmap when the goal is to understand what Brainiac is and how its internal concepts fit together.

## One-line Idea

Brainiac is an AI-first local second-brain backend over plain files.

It helps an operator work with a vault through:

- disposable indexes
- bounded retrieval
- duplicate/canonicalization logic
- synthesis notes
- controlled write workflows

It is not an Obsidian replacement and not a prompt dump of the whole vault.

## Why It Exists

Large vaults create context debt.

Without a local retrieval layer, an AI tends to:

- read too many files
- lose track of prior conclusions
- create duplicate notes
- make expensive synthesis passes repeatedly

Brainiac exists to reduce that cost and make operator behavior reproducible.

## Core Objects

### Vault

The user's local knowledge base.

Typical source-of-truth formats:

- Markdown
- SQLite
- JSON
- YAML
- CSV
- source assets

### Source Note

A Markdown note that is treated as primary evidence or working memory.

Source notes are truth.
They are not derived summaries.

Source notes are the default note role, and they should still be marked explicitly with `brainiac_role: source`.

### Umbrella Note

A Markdown master list or index note that points at several source notes.

Umbrella notes are ordinary user notes with an explicit `brainiac_role: umbrella` frontmatter marker.
They can be used for navigation and aggregation, but they are not derived memory.

### Index

A disposable SQLite cache built from the vault.

The index stores:

- file metadata
- headings
- frontmatter metadata
- wikilinks
- tags
- tasks
- full-text search rows

The index is not truth.
It is rebuildable from source files.

### Search / Inspect / Related

Bounded retrieval tools over the index.

They exist so the operator does not need to read the whole vault.

### Duplicate

Two notes that overlap enough to need special handling.

There are two different classes:

- exact duplicate: same content hash, different path
- semantic duplicate: different content, overlapping topic or intent

These must not be treated the same way.

### Canonical Note

The preferred note path that Brainiac should use for future links, synthesis, and edits when duplicate clusters exist.

Canonicalization is a working preference, not an automatic deletion rule.
For exact duplicates, canonicalization should affect retrieval, synthesis, and future write targeting before any cleanup workflow exists.
It should not be confused with automatic vault repair.

### Synthesis Note

A derived-memory note that summarizes current understanding of a topic.

It is not raw evidence.

It should contain things like:

- current stance
- key points
- decisions
- contradictions
- open questions
- source links
- source snapshots

Synthesis notes are how Brainiac avoids re-synthesizing the same topic from scratch every time.
They are context, not a default write target for new source notes.

Synthesis notes should be marked explicitly, for example with `brainiac_role: synthesis`.

### Archive Root

A configured folder that belongs to inert historical storage.

Archive roots are trash-like history. Brainiac excludes them from scanning and indexing, so archive files do not appear in normal search, routing, duplicates, synthesis, or maintenance.

Brainiac expects every indexed Markdown note to carry an explicit `brainiac_role` marker and can surface notes that do not.

### Generated Artifact

A derived output such as:

- report
- dashboard
- HTML view
- queue draft

Generated artifacts are not canonical truth.

### Operator

Jarvis is the default operator name used in this project.

The operator:

- asks narrow questions
- retrieves bounded context
- creates or refreshes synthesis
- proposes or applies writes safely

## Internal Relationships

This is the most important mental model:

```text
source notes and structured files = truth
index = disposable retrieval cache
synthesis notes = derived memory
generated artifacts = views and staging outputs
operator = actor using all of the above
```

## Default Retrieval Strategy

Brainiac should not start by reading files directly.

Default order:

1. check index state
2. search or inspect
3. read a synthesis note first if one exists
4. read selected raw notes only when needed
5. write only after policy and duplicate checks

## Duplicate Strategy

### Exact Duplicates

If two notes have identical content:

- choose one canonical path
- use the canonical path in retrieval and synthesis
- keep shadow copies until cleanup is explicitly approved

### Semantic Duplicates

If two notes overlap in meaning but not in content:

- do not auto-merge immediately
- read both
- preserve unique details
- reconcile via synthesis first
- compare source notes against source notes; synthesis notes are handled separately as derived memory freshness, not as ordinary duplicate candidates
- only then propose merge or cleanup
- sibling notes that share a folder subtree are expected to share structure; for those, name similarity must carry much more weight than template similarity before a duplicate is reported

## Synthesis Strategy

Synthesis should be topic-level, not file-per-file.

Good synthesis behavior:

- use a small number of relevant source notes
- prefer strong sources over weak lexical mentions
- update synthesis when source evidence changes
- treat synthesis as the first context layer for future work
- let stale synthesis be detected from source snapshot mismatch, not from semantic duplicate detection

Bad synthesis behavior:

- synthesize every note
- feed whole folders into the LLM
- treat weak mentions as equal evidence
- rewrite source notes before synthesis clarifies the topic

## Cost Model

Python/SQLite should do the cheap work:

- indexing
- freshness checks
- duplicate detection
- canonicalization
- source candidate selection
- stale-synthesis detection

The LLM should do the expensive work only after narrowing:

- topic-level reasoning
- synthesis drafting
- contradiction analysis
- merge/reconciliation proposals

This is how Brainiac keeps synthesis from becoming unreasonably expensive.

## Safety Model

Brainiac should decide some things automatically and escalate others.

Usually safe to decide automatically:

- whether the index is stale
- whether two notes are exact duplicates
- which exact duplicate path should be canonical for retrieval/synthesis
- whether synthesis is stale based on source snapshots

Should usually require review:

- rewriting existing links toward canonical targets
- deleting duplicate notes
- merging semantic duplicates
- retiring duplicate source notes after synthesis reconciliation
- rewriting canonical notes
- moving large note sets
- modifying sensitive notes

## What Brainiac Is Not

Brainiac is not:

- an Obsidian clone
- a graph database project in disguise
- a reason to load the whole vault into context
- a license for autonomous vault rewrites
- a generated HTML memory system

## What A New Chat Should Remember

If a new chat remembers only a few things, they should be these:

1. the index is a cache, not truth
2. source notes are truth
3. synthesis notes are derived memory
4. exact duplicates should be canonicalized automatically for retrieval
5. semantic duplicates should usually go through synthesis or reconciliation before cleanup
6. use bounded retrieval before reading files
7. use LLM reasoning only after Python narrowed the evidence set
