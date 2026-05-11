# Brainiac Context Brief

This file preserves the important context from the original design conversation so future chats can resume without repeating the whole discussion.

## Why Brainiac Exists

The initial question was whether a second brain should move beyond Markdown into richer formats like HTML. The conclusion was not "replace Markdown with HTML".

The stronger idea is:

```text
Markdown / SQLite / JSON / YAML / CSV = durable source of truth
HTML = generated presentation layer
Brainiac = local retrieval, routing, synthesis, and safe-write backend for Jarvis
```

The key problem is context debt. Once a vault has hundreds or thousands of notes, an AI cannot read all files every time. It needs a local query layer that returns bounded context.

## Main Hypothesis

Brainiac should be a local memory substrate for AI agents:

- parse a vault;
- build disposable indexes;
- expose bounded tools;
- retrieve relevant notes/sections;
- route new information;
- detect duplicates;
- maintain persistent synthesis;
- generate useful HTML views;
- write through explicit policies and logs.

## Roles

```text
Obsidian = human-facing editor and vault UI
Brainiac = memory/retrieval backend
Jarvis = default operator
Markdown/SQLite/JSON = truth
HTML = view/artifact
```

Jarvis and Brainiac are separate layers. Jarvis operates. Brainiac remembers, retrieves, routes, and exposes safe tools.

Brainiac should remain usable as a generic core, but this project uses `Jarvis` as the default operator name.

## Important Design Decisions

### Do not build an Obsidian clone

Obsidian already handles editing, local vault storage, backlinks UI, graph UI, properties, Bases, Dataview, plugins, and human navigation.

Brainiac should sit next to it and work over files.

### Do not load the whole index into context

The index is a backend, not a prompt file.

Bad:

```text
AI reads vault_index.json
AI tries to reason over everything
```

Good:

```text
AI calls brain.search / brain.route / brain.related
Brainiac returns compact candidates, snippets, paths, scores, and reasons
AI reads only selected sections/files
```

### Start with SQLite, not a graph database

"Graph" means relationships, not a mandatory graph DB.

The first version can store links as:

```text
links(from_path, to_path, type, count)
```

Cycles are safe if graph traversal is bounded by `visited`, `max_depth`, `max_nodes`, and token/result budgets.

### Start with structural retrieval, not embeddings

Embeddings are useful, but not first.

The first valuable index can extract:

- files;
- titles;
- headings;
- wikilinks;
- backlinks;
- tags;
- tasks;
- frontmatter;
- modified times;
- hashes;
- empty-note status.

Semantic search can be added after structural/lexical retrieval proves useful.

### Synthesis is different from RAG

RAG retrieves raw context but does not preserve understanding.

Brainiac should maintain stable synthesis notes for important topics:

- current stance;
- decisions;
- contradictions;
- open questions;
- source links.

These can be plain Markdown. No separate synthesis DB is required initially.

### HTML is useful, but not canonical

HTML is valuable for:

- dashboards;
- explainers;
- interactive triage boards;
- comparison views;
- visualizations;
- generated reports.

But HTML should be generated from source data and should not become durable truth unless there is a specific reason.

Best pattern:

```text
source data -> generated HTML view -> export/copy patch -> controlled write through Brainiac/operator
```

## Lessons From Inspecting the User's Personal Vault

The inspected vault had:

- `0_Inbox/` for raw personal/work captures;
- `1_Projects/`;
- `2_Areas/` for food, health, family, travel, taxes, social topics, work remnants;
- `3_Resources/`;
- `ibooks-highlights/`;
- some empty placeholder notes;
- low current graph density;
- useful `#todo/now`, `#todo/soon`, `#todo/someday` tags;
- noisy imported highlight anchors like `#epubcfi`.

Implication:

- do not overbuild graph/embeddings first;
- start with inventory, inbox cleanup, task extraction, routing, and synthesis of highlights;
- treat health/family as sensitive and mostly read-only unless explicitly requested.

## Good Initial Use Cases

- Route inbox items into existing areas or new notes.
- Extract tasks across the vault.
- Detect stale/empty notes.
- Turn book highlights into synthesis notes.
- Produce a vault health dashboard.
- Suggest duplicate/canonical notes.
- Generate HTML views from indexed data.

## Bad Initial Use Cases

- Full autonomous vault reorganization.
- Autonomous rewriting of health/family notes.
- Daily briefing spam before retrieval quality is proven.
- A complex graph database before SQLite is insufficient.
- Replacing Markdown with HTML.
- Building an Obsidian clone.

## Current Best Formulation

Brainiac is an AI-first local knowledge operating system over plain files, with disposable indexes, bounded retrieval tools, persistent synthesis notes, controlled writes, and generated HTML views.
