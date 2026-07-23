# Brainiac Development Plan

## Completed foundation

- Read-only incremental vault inventory in SQLite.
- Bounded FTS search, inspect, read, and related commands.
- Dry-run routing, collision checks, exact duplicate canonicalization, and semantic duplicate diagnostics.
- Structure profiles and read-only maintenance reporting.

## Completed: umbrella-first operation

- [x] Make new write suggestions default to `brainiac_role: source`.
- [x] Surface a note’s role and umbrella backlinks in `inspect`.
- [x] Define the post-update operator rule: inspect existing umbrella backlinks and propose an update only when navigation or a choice rule changed.
- [x] Keep umbrella creation explicit; do not create them from simple note counts or folder similarity.
- [x] Use structure profiles to keep routing destinations explicit before adding retrieval complexity.

## Current focus: field validation of the operator loop

- [ ] Exercise real workflows: find information, create or update a source, inspect its umbrella backlinks, and run maintenance.
- [ ] When lexical retrieval is empty or weak, first use bounded query expansion: translate the query, try a close synonym, or search by category or location before reading an umbrella.
- [ ] Record each retrieval failure with the original query, the expected note, and the successful fallback; promote only repeated failures into product work.
- [ ] Improve routing only from observed operator failures, not from speculative folder rules.

## Later, only if proven useful

- a small query-expansion layer for recurring multilingual or synonym misses;
- optional semantic search;
- MCP/local service once the CLI surface is stable;
- Obsidian convenience integration;
- lightweight maintenance validation after edits.

## Non-goals

- an Obsidian clone;
- autonomous vault rewrites;
- mandatory derived-summary notes or background summary maintenance.
