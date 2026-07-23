# Brainiac Development Plan

## Completed foundation

- Read-only incremental vault inventory in SQLite.
- Bounded FTS search, inspect, read, and related commands.
- Dry-run routing, collision checks, exact duplicate canonicalization, and semantic duplicate diagnostics.
- Structure profiles and read-only maintenance reporting.

## Current focus: umbrella-first operation

- [ ] Make new write suggestions default to `brainiac_role: source`.
- [ ] Surface a note’s role and umbrella backlinks in `inspect`.
- [ ] Define the post-update operator rule: inspect existing umbrella backlinks and propose an update only when navigation or a choice rule changed.
- [ ] Keep umbrella creation explicit; do not create them from simple note counts or folder similarity.
- [ ] Improve routing with structure profiles before adding more retrieval complexity.

## Later, only if proven useful

- optional semantic search;
- MCP/local service once the CLI surface is stable;
- Obsidian convenience integration;
- lightweight maintenance validation after edits.

## Non-goals

- an Obsidian clone;
- autonomous vault rewrites;
- mandatory derived-summary notes or background summary maintenance.
