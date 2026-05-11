# Concept: AI-first local second brain

## One-line Idea

Build a local second-brain backend that lets an AI agent work with a personal knowledge vault through precise tools instead of rereading the whole vault every time.

## What This Is

Brainiac is not an Obsidian clone.

It is a local memory/retrieval layer over plain files:

```text
local vault -> disposable indexes -> bounded tools -> Jarvis -> optional views
```

Obsidian can remain the human-facing editor. Brainiac provides the intelligence layer.

## Core Problem

Large personal vaults create context debt. An AI agent cannot read hundreds or thousands of files every time it needs to answer a question, route a note, or resume a topic.

Naive model:

```text
read many files -> fill context -> reason once -> forget
```

Brainiac model:

```text
ask narrow question -> retrieve bounded context -> read selected sections -> write through controlled operations
```

## Key Principles

### Source of Truth Stays Simple

Durable knowledge should live in portable formats:

- Markdown for narrative knowledge;
- SQLite/JSON/YAML/CSV for structured domains;
- normal files for assets;
- HTML for generated presentation only.

### Indexes Are Disposable

Indexes are caches. If deleted, they must be rebuildable from the vault.

### Retrieval Is a Tool, Not a Prompt Dump

The AI should never load the full index. It should call tools that return bounded results.

### Graph Means Relationships, Not Hype

The first graph can be a simple table:

```text
links(from_path, to_path, type, count)
```

Cycles are normal. Traversal must always use `visited`, `max_depth`, `max_nodes`, and result budgets.

### Synthesis Means Persistent Understanding

RAG retrieves context but does not preserve conclusions. Brainiac should maintain synthesis notes for important topics:

- current stance;
- decisions;
- contradictions;
- open questions;
- links to raw sources.

### HTML Is a View Layer

HTML is useful for dashboards, explainers, comparison grids, and interactive triage boards. It should be generated from source data and should not become canonical memory.

## Relationship to Obsidian

Use Obsidian for:

- editing Markdown;
- human browsing;
- backlinks and graph UI;
- properties, Bases, Dataview;
- plugin ecosystem.

Brainiac should work even if Obsidian is closed by parsing local files directly.

Later, an Obsidian plugin can expose editor state, metadata cache, command palette actions, and dashboards.

## Target Shape

```text
Brainiac/
  config/
    vault.yml
    routing.yml
    policies.yml
  docs/
    concept.md
    development-plan.md
  memory/
    synthesis/
    generated/
    queue/
    index/
    logs/
```

## Non-goals

- Build a full Obsidian clone.
- Replace Markdown with HTML.
- Load the whole vault into every chat.
- Build a complex graph database before SQLite is insufficient.
- Generate endless daily briefs that no one reads.
- Let autonomous agents rewrite operating rules without review.
