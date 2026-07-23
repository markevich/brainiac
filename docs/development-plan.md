# Brainiac Development Plan

This plan evolves Brainiac through small useful milestones. Markdown and structured files remain truth; the SQLite index is a disposable cache. Do not add complexity until the preceding workflow has been proven useful.

## Phase 0: Skeleton and Doctrine — complete

Goal: define what Brainiac is and what it is not.

- [x] Create repository skeleton.
- [x] Write the core concept and operator contract.
- [x] Define initial vault, routing, and policy configs.
- [x] Add operation logging and a Codex/agent entrypoint.
- [x] Split development context from operator context.

Exit criterion: a future AI session can read `README.md`, `operator.md`, and `docs/concept.md` and understand the project.

## Phase 1: Read-only Vault Inventory — complete

Goal: understand an existing vault without changing it.

Indexing model:

- `scan` maintains the disposable SQLite index from source files.
- Compatible indexes update incrementally: changed Markdown files are parsed, deleted paths are removed, and wikilinks are resolved globally from indexed link rows.
- `--full-rebuild` is available for an intentional clean rebuild.
- Brainiac does not silently reindex at the start of every session; later commands read the existing index and report when it is stale or missing.

Completed work:

- [x] Scan a vault path and collect files, paths, sizes, mtimes, hashes, and empty-note state.
- [x] Extract headings, wikilinks, tags, tasks, Markdown frontmatter, and searchable text.
- [x] Classify resolved, missing, and ambiguous wikilinks.
- [x] Store inventory in SQLite and generate an inventory report.

Exit criterion: Brainiac can answer “what is in this vault?” without loading the vault into model context.

```bash
PYTHONPATH=src python3 -m brainiac scan --vault-root /path/to/vault
PYTHONPATH=src python3 -m brainiac index info --check-filesystem
```

## Phase 2: Bounded Search and Inspect — complete

Goal: give the operator useful retrieval tools before embeddings.

Requirements and completed work:

- [x] Require SQLite FTS5 and emit a clear setup error when unavailable.
- [x] Search titles, headings, paths, tags, tasks, and text snippets through FTS.
- [x] Implement bounded `inspect`, `read`, and `related` commands.
- [x] Surface outgoing links, backlinks, ambiguous-link warnings, exact-duplicate groups, and canonical paths.
- [x] Bound result counts, section reads, and snippet budgets.
- [x] Report index freshness without scanning on every retrieval call.

Exit criterion: the operator can find relevant notes and read selected sections without broad filesystem reads.

```bash
PYTHONPATH=src python3 -m brainiac search "query"
PYTHONPATH=src python3 -m brainiac inspect path/to/note.md
PYTHONPATH=src python3 -m brainiac read path/to/note.md --section "Heading"
PYTHONPATH=src python3 -m brainiac related path/to/note.md
```

## Phase 3: Routing and Dedupe — complete baseline

Goal: help place new information into the vault without writing automatically.

- [x] Define routing rules in `config/routing.yml`.
- [x] Implement `route(content)` with scored candidate destinations and reasons.
- [x] Implement lexical and metadata duplicate diagnostics.
- [x] Produce dry-run create, update, or review suggestions.
- [x] Detect title and basename collisions before a proposed write.
- [x] Generate shortest unique wikilinks for Brainiac-created suggestions.
- [x] Keep sensitive destinations and short domain tokens in config rather than source code.
- [x] Log real write operations outside the router.

Exit criterion: given a new note or inbox item, Brainiac can suggest a destination and overlapping notes without proposing ambiguous links or blind creates.

```bash
PYTHONPATH=src python3 -m brainiac route "# New note..."
PYTHONPATH=src python3 -m brainiac route --file /path/to/draft.md
PYTHONPATH=src python3 -m brainiac find-duplicates "# New note..."
```

## Phase 4: Vault Structure Model — in progress

Goal: define a generic taxonomy that makes routing, retrieval, and safe writes portable across vaults.

Completed work:

- [x] Define configurable roots for inbox, projects, areas, resources, archive, generated output, and queue.
- [x] Add routing config for role roots, sensitive domains, important short tokens, and disabled destinations.
- [x] Generate compact area/project/resource profiles: path, role, note and file counts, tags, terms, representative notes, routing coverage, and sensitivity.
- [x] Add `brainiac structure` and maintenance findings for unconfigured profiles.
- [x] Use profile findings to make local routing destinations explicit.

Remaining work:

- [ ] Study PARA and alternatives only to improve portable guidance, not to force a vault migration.
- [ ] Add optional recent-activity summaries and aliases/domain hints as local overrides.
- [ ] Use profile evidence as an additional routing signal when observed routing failures justify it.
- [ ] Support sparse vaults with generic role templates and “candidate new area” suggestions.
- [ ] Document migration-safe recommendations: propose, do not move files automatically.

Exit criteria:

- Brainiac can explain the role of each configured path.
- Routing remains portable by role while local paths stay configuration-only.
- Source code contains no user-specific vault assumptions.

```bash
PYTHONPATH=src python3 -m brainiac structure
```

## Phase 5: Source and Umbrella Operation — complete baseline

Goal: retain human-useful navigation without creating a compulsory derived-memory layer.

Model:

```text
source notes = facts, captures, cards, tasks, observations
umbrella notes = explicit navigation, status, categories, and choice guidance
SQLite index = retrieval cache
Jarvis = operator
```

Completed work:

- [x] Make `source` the default role for new route suggestions.
- [x] Allow only explicit `source` and `umbrella` role markers.
- [x] Surface a note’s role and umbrella backlinks in `inspect`.
- [x] Maintain role-marker diagnostics in `maintenance report`.
- [x] Define the post-update rule: inspect umbrella backlinks after a material source change and propose an update only when navigation, status, categories, ratings, or a choice rule changed.
- [x] Keep umbrella creation explicit. Related notes, folder similarity, or note count alone do not justify one.
- [x] Remove the former synthesis subsystem and its derived-note role.

Exit criteria:

- A source update can be connected to an existing umbrella without global scans or background rewriting.
- The operator can explain why an umbrella is useful or why no umbrella update is needed.

## Phase 5.5: Canonicalization and Vault Maintenance — complete baseline

Goal: keep a vault clean through diagnostics and small, reviewable corrections rather than a heavyweight repair pipeline.

Completed work:

- [x] Report index freshness through `index info`.
- [x] Detect exact duplicate Markdown groups and choose canonical paths.
- [x] Surface canonical paths in `inspect` and use them in related-note retrieval.
- [x] Separate exact duplicate groups from semantic-overlap candidates.
- [x] Provide `duplicates list` and bounded duplicate inspection.
- [x] Provide `maintenance report` for empty directories, ambiguous and missing links, unconfigured profiles, role markers, duplicate groups, and semantic candidates.
- [x] Keep the normal loop lightweight: report → operator review/edit → scan → report.

Remaining work:

- [ ] Add an optional batch-maintenance assistant that can draft multiple low-risk edits, log writes, and revalidate afterwards.
- [ ] Define a compact format for recording a semantic-duplicate resolution without forcing any merge or deletion.

Exit criteria:

- Brainiac can explain current vault defects without broad manual inspection.
- Operators can move from a report to explicit edits and back to validation safely.

```bash
PYTHONPATH=src python3 -m brainiac duplicates list
PYTHONPATH=src python3 -m brainiac maintenance report
```

## Phase 6: Field Validation of the Operator Loop — current focus

Goal: prove that the existing CLI and source/umbrella model help in real work before adding retrieval complexity.

Tasks:

- [ ] Exercise real workflows: find information, create or update a source, inspect its umbrella backlinks, and run maintenance.
- [ ] Test a few low-risk domains such as food, travel, 3D printing, or book highlights.
- [ ] For every empty or weak lexical result, try bounded query expansion first: translation, close synonym, category, or location term; then inspect a matching umbrella and read only the needed section.
- [ ] Record the original query, expected note, successful fallback, and whether the result was good enough.
- [ ] Treat a repeated retrieval miss as evidence for product work; do not add a feature for one anecdote.
- [ ] Improve routing only from observed operator failures, not speculative folder rules.

Exit criteria:

- Brainiac produces a result the operator would reuse in at least one ordinary domain.
- The team has concrete evidence for, or against, a small query-expansion feature.

## Phase 7: Query Expansion and Optional Semantic Search

Goal: improve recall only when Phase 6 evidence shows lexical retrieval is insufficient.

Order of consideration:

1. Add a small, inspectable query-expansion layer for recurring translation, synonym, or transliteration misses.
2. Evaluate semantic search only if expansion and structural retrieval still miss useful results.

Potential tasks for semantic search:

- [ ] Choose an embedding provider or local model.
- [ ] Track model version and reindex behavior.
- [ ] Chunk by heading sections, not only whole files.
- [ ] Store vectors in a small local store or SQLite extension.
- [ ] Combine semantic candidates with structural and lexical ranking.

Exit criterion: measured recall or answer quality improves enough to justify the additional complexity.

## Phase 8: MCP or Local Service

Goal: expose a stable CLI surface as proper AI tools once it has been proven manually.

- [ ] Decide MCP versus local HTTP only after CLI workflows stabilize.
- [ ] Wrap stable read commands as tools.
- [ ] Add explicit, policy-checked write operations only when the review workflow is mature.
- [ ] Preserve operation logs and sensitive-domain checks.

Exit criterion: an operator can use Brainiac as a tool provider without losing bounded retrieval or write safety.

## Phase 9: Obsidian Convenience Integration

Goal: improve the Obsidian experience without making Obsidian the backend.

- [ ] Evaluate Local REST API versus a small plugin.
- [ ] Add “route current note” and “show related notes” workflows only if the CLI equivalents prove useful.
- [ ] Optionally read Obsidian metadata cache where it adds value.
- [ ] Open generated reports or focused notes as a convenience, not as source of truth.

Exit criterion: Brainiac is more convenient inside Obsidian while staying a plain-file system.

## Phase 10: Maintenance Automation

Goal: add automation only after manual maintenance and retrieval workflows are demonstrably useful.

- [ ] Offer scheduled or explicit maintenance reports without notification spam.
- [ ] Detect stale generated artifacts and unsupported links.
- [ ] Detect likely umbrella updates from changed linked sources, but always propose rather than rewrite.
- [ ] Add a first-class LLM batch-edit helper only after dry-run and post-edit validation are trusted.
- [ ] Provide simple reindex and validation commands after edits.

Exit criterion: Brainiac helps keep navigation and vault structure coherent without autonomous rewrites or mandatory approval machinery.

## Non-goals

- An Obsidian clone.
- Autonomous vault rewrites.
- Mandatory derived-summary notes or background summary maintenance.
- A forced PARA migration or hardcoded personal vault structure.
