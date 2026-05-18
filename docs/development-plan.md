# Brainiac Development Plan

This plan is intentionally lightweight. The goal is to evolve the concept through small useful milestones, not design a giant system upfront.

## Phase 0: Skeleton and Doctrine

Goal: define what Brainiac is and what it is not.

Tasks:

- [x] Create repository skeleton.
- [x] Write core concept.
- [x] Write operator contract.
- [x] Define initial vault, routing, and policy configs.
- [x] Add initial operation log.
- [x] Add notes from early design discussion.
- [x] Add Codex/agent entrypoint.
- [x] Split development context from operator context.

Exit criteria:

- A future AI session can read `README.md`, `operator.md`, and `docs/concept.md` and understand the project.

## Phase 1: Read-only Vault Inventory

Goal: understand an existing vault without changing it.

Indexing model:

- `scan` maintains the disposable SQLite index from source files.
- Compatible existing indexes are updated incrementally: Brainiac walks the vault tree, reparses changed Markdown files, removes deleted paths, and re-resolves wikilinks globally from indexed link rows.
- `--full-rebuild` is available when a clean rebuild is intentionally desired.
- Brainiac does not reindex automatically at the start of every agent/session.
- Later retrieval commands read the existing index and should ask the user to run `scan` if it is missing or stale.

Tasks:

- [x] Build a CLI command that scans a vault path.
- [x] Collect files, paths, sizes, mtimes, hashes, and empty-note status.
- [x] Extract Markdown headings.
- [x] Extract wikilinks and classify resolved, missing, and ambiguous links.
- [x] Extract tags.
- [x] Extract Markdown tasks.
- [x] Write results to SQLite.
- [x] Generate a simple text or HTML inventory report.

Exit criteria:

- Brainiac can answer "what is in this vault?" without reading all files into AI context.

Current command:

```bash
PYTHONPATH=src python3 -m brainiac scan --vault-root /path/to/obsidian-vault
```

## Phase 2: Bounded Search and Inspect

Goal: give the AI useful retrieval tools before adding embeddings.

Runtime requirement:

- SQLite FTS5 support is required.
- Brainiac should check FTS5 availability before creating/searching the index and exit with a clear setup error if unavailable.
- Do not maintain a non-FTS fallback unless a real target environment requires it.

Tasks:

- [x] Add an FTS5 runtime requirement check.
- [x] Add FTS5 tables for searchable Markdown content and metadata.
- [x] Implement lexical search over titles, headings, paths, tags, and text snippets.
- [x] Implement `inspect(path)` for metadata, headings, links, backlinks, tasks.
- [x] Implement `read(path, section?)`.
- [x] Implement `related(path)` using links, backlinks, folder proximity, tags, and lexical overlap.
- [x] Enforce result limits and snippet budgets.
- [x] Surface ambiguous links as warnings, with candidate paths and an Obsidian-compatible preferred path where possible.

Exit criteria:

- The AI can find relevant notes and read selected sections without scanning the whole vault.

Implemented commands:

```bash
PYTHONPATH=src python3 -m brainiac search "query"
PYTHONPATH=src python3 -m brainiac inspect path/to/note.md
PYTHONPATH=src python3 -m brainiac read path/to/note.md --section "Heading"
PYTHONPATH=src python3 -m brainiac related path/to/note.md
PYTHONPATH=src python3 -m brainiac index info
PYTHONPATH=src python3 -m brainiac index info --check-filesystem
```

Implementation notes:

- `scan` creates a searchable FTS5 table from Markdown path, title, headings, tags, tasks, and body text.
- `search` reads the existing index only; it does not rescan the vault.
- `inspect` returns bounded metadata: file facts, headings, tags, tasks, outgoing links, backlinks, and ambiguous-link warnings.
- `inspect` now also surfaces exact duplicate groups and the currently chosen canonical path for exact duplicates.
- `read` returns a whole file or a single Markdown heading section with a max-character budget.
- `related` combines outgoing links, backlinks, preferred ambiguous-link candidates, shared tags, bounded lexical candidates, and exact-duplicate canonicalization.
- Ambiguous wikilinks keep all candidates and a deterministic preferred path. This is a best-effort Obsidian-compatible guess, not a guarantee of Obsidian's internal resolver.
- Generic task tags such as `#todo/now` are intentionally weak relatedness signals so they do not dominate explicit links.
- `index info` reports index freshness metadata and can optionally compare the indexed file set to the live vault filesystem.
- CLI errors are short user-facing messages instead of Python tracebacks for expected cases such as missing indexes, missing paths, and missing sections.

Live-vault check:

- Rebuilt the external Obsidian vault index successfully.
- Search worked for Cyrillic terms, task tags, ticket-like tokens, body text, and path/title terms.
- `inspect` correctly surfaced existing ambiguous links with candidates.
- `read --section` returned bounded sections.
- `related` initially over-ranked generic inbox/task-tag neighbors; scoring was tuned so explicit links and preferred ambiguous candidates rank first.

## Phase 3: Routing and Dedupe

Goal: help place new information into the vault.

Tasks:

- [x] Define routing rules in `config/routing.yml`.
- [x] Implement `route(content)` returning candidate destinations and reasons.
- [x] Implement `find_duplicates(content)` using lexical similarity and metadata.
- [x] Add dry-run write suggestions.
- [x] Add note-name collision checks before any proposed create/write operation.
- [x] Define unique-title generation for Brainiac-created notes.
- [x] Generate links in a shortest-unique format so Brainiac-created links do not introduce ambiguity.
- [x] Add write log format.

Exit criteria:

- Given a new note or inbox item, Brainiac can suggest where it belongs and what existing notes may overlap.
- Brainiac does not propose creating Markdown notes or links that introduce duplicate basename ambiguity.

Implemented commands:

```bash
PYTHONPATH=src python3 -m brainiac route "# New note..."
PYTHONPATH=src python3 -m brainiac route --file /path/to/draft.md
PYTHONPATH=src python3 -m brainiac find-duplicates "# New note..."
PYTHONPATH=src python3 -m brainiac find-duplicates --file /path/to/draft.md
```

Implementation notes:

- `route` reads the existing index and `config/routing.yml`; it does not rescan or write to the vault.
- Route candidates include destination scores, reasons, duplicate candidates, and a dry-run suggestion to create, update, or review an existing note.
- Folder destinations generate a unique Markdown filename from the proposed title.
- Existing same-title notes or basename collisions turn the suggestion into `review` instead of blindly proposing a new file.
- Suggested wikilinks use the shortest unique Obsidian-compatible form: `[[Title]]` when the basename is unambiguous, otherwise `[[folder/Title]]`.
- Duplicate detection is lexical and metadata-based. It intentionally avoids embeddings for this phase.
- Sensitive destinations and short domain tokens are configured in `config/routing.yml`, not hardcoded in source.
- Disabled destination sections, such as generated artifacts, are configured in `config/routing.yml` and excluded from source-note routing.
- Low-confidence routes are explicitly marked as inbox/new-area candidates instead of pretending an existing area is a good fit.
- Write operations are not implemented yet, but their append-only JSONL audit format is defined in `docs/write-log-format.md`.

## Phase 4: Vault Structure Model

Goal: define a generic vault taxonomy that makes routing, retrieval, and safe writes work across different people and vaults.

Research candidates:

- PARA: Projects, Areas, Resources, Archives;
- Johnny Decimal;
- Zettelkasten-style permanent/literature/fleeting notes;
- domain-first vaults;
- hybrid models with inbox, active work, durable areas, resources, generated artifacts, and archive.

Tasks:

- [ ] Study how PARA and alternatives map to Brainiac use cases.
- [ ] Define Brainiac's recommended generic vault shape without requiring users to adopt it exactly.
- [x] Separate universal roles from user-specific paths: inbox, projects, areas, resources, archive, generated, synthesis, queue.
- [x] Add an initial routing config schema for role roots, sensitive domains, important short tokens, and disabled destination sections.
- [x] Define an initial runtime vault map over roles, areas, projects, resources, and synthesis roots.
- [x] Generate compact area/project/resource profiles from existing notes: path, role, tags, top terms, representative notes, and sensitive flag.
- [ ] Add profile summaries and recent activity.
- [ ] Add aliases and domain-specific hints as optional local overrides.
- [ ] Use the vault map as the first routing layer: rank candidate areas/projects by profile before selecting a destination note.
- [ ] Treat manual hints as optional local overrides, not as the primary multilingual routing strategy.
- [ ] Support empty or sparse vaults with generic role templates and "candidate new area" suggestions.
- [x] Add a command or report that diagnoses a vault's structure against the recommended model.
- [ ] Document migration-safe recommendations: suggest, do not move files automatically.
- [ ] Revisit Phase 3 scoring once role metadata exists, so routing is not over-dependent on folder names.

Exit criteria:

- Brainiac can explain what role each configured vault path plays.
- Routing rules can be portable across vaults by role, while local paths remain config-only.
- No source code contains user-specific vault path assumptions.
- Routing decisions can be made from compact area/project profiles instead of hardcoded multilingual keyword dictionaries.

Implemented command:

```bash
PYTHONPATH=src python3 -m brainiac structure
```

Implementation notes:

- `structure` reads the existing index and `config/routing.yml`; it does not rescan or write to the vault.
- Role roots are config-driven, with observed defaults used only as a compatibility fallback.
- Profiles currently include role, path, note count, file count, routing coverage status, sensitive flag, top tags, top terms, and representative notes.
- Flat source collections such as imported book highlights are treated as one resource profile instead of one profile per file.
- The command reports unconfigured profiles and recommendations such as missing routing destinations for detected areas.

## Phase 5: Synthesis Primitives

Goal: make persistent understanding a first-class retrieval object, not a late-stage reporting feature.

Why this phase exists:

- Search answers "what raw context is relevant right now?"
- Synthesis answers "what have we already concluded about this topic over time?"
- Without synthesis, Brainiac repeats RAG behavior: retrieve raw notes, reason once, then forget the reasoning.
- With synthesis, Jarvis can read compact current understanding first, then inspect raw sources only for gaps, details, or verification.

Core model:

```text
raw notes/highlights/captures = evidence
synthesis notes = current understanding
index = retrieval mechanism
Jarvis = operator that uses all three
```

Retrieval behavior:

- Synthesis notes should be indexed and searchable like normal Markdown.
- Topic-matching synthesis notes should be boosted above raw source notes in search/related results.
- `inspect` should show whether a source note is referenced by synthesis notes.
- `related` should include synthesis notes that cite or summarize the current note.
- Jarvis should read a relevant synthesis note first, then use raw sources for verification or details.

Tasks:

- [x] Define synthesis note format: current stance, key points, decisions, open questions, contradictions, sources, last reviewed.
- [x] Define frontmatter or metadata convention for synthesis notes.
- [x] Add synthesis roots to config and index them as a distinct role/type.
- [x] Track source references from synthesis notes to raw notes.
- [x] Track source hash/mtime snapshots used by each synthesis note.
- [x] Implement `synthesis list`.
- [x] Implement `synthesis inspect <topic-or-path>`.
- [x] Implement `synthesis stale` to detect synthesis notes whose sources changed.
- [x] Implement `synthesis suggest <topic-or-path>` as dry-run only.
- [x] Make `search` and `related` surface relevant synthesis notes before raw sources when appropriate.
- [x] Add review-before-apply policy for synthesis writes.
- [x] Document that synthesis is derived memory, not raw evidence.

Exit criteria:

- Brainiac can preserve conclusions over time instead of making Jarvis re-synthesize everything on each query.
- Jarvis can use a synthesis note as the first context layer for a topic.
- Brainiac can explain which raw sources support a synthesis note and whether that synthesis may be stale.

Implemented commands:

```bash
PYTHONPATH=src python3 -m brainiac synthesis list
PYTHONPATH=src python3 -m brainiac synthesis inspect <topic-or-path>
PYTHONPATH=src python3 -m brainiac synthesis stale
PYTHONPATH=src python3 -m brainiac synthesis suggest <topic-or-path>
```

Implementation notes:

- Synthesis notes are discovered by configured `synthesis_roots` or `brainiac_type: synthesis` frontmatter.
- Markdown frontmatter is indexed into `markdown_metadata`.
- Synthesis source references currently come from resolved wikilinks in synthesis notes.
- Optional `source_snapshots` frontmatter entries use `path|sha256|mtime`; `synthesis stale` compares indexed source hashes with those snapshots.
- `inspect` on a raw source now reports synthesis notes that reference it.
- `related` gives direct synthesis references a strong score and lightly boosts synthesis notes with lexical overlap.
- `search` boosts frontmatter-marked synthesis notes above raw notes when they match the same query.
- `synthesis suggest` is dry-run only. It proposes a create/update target, canonicalized raw source candidates, source snapshots, and a Markdown skeleton, but does not write files.
- Exact duplicate source notes are canonicalized before they become synthesis evidence, so the same evidence blob is not proposed twice under different paths.
- `config/policies.yml` defines synthesis writes as review-before-apply derived memory writes that require source links, source snapshots, and explicit confirmation.

Live-vault check:

- Incremental scan worked on a configured real vault without reparsing unchanged Markdown files.
- `index info` surfaced exact duplicate groups and filesystem freshness state.
- Including a second Softswiss subtree exposed ambiguous wikilinks and exact duplicate clusters across old and new note locations.
- `synthesis suggest` collapsed exact duplicate sources to one canonical note and downgraded body-only lexical matches to weak context.

## Phase 5.5: Canonicalization and Vault Maintenance

Goal: turn duplicate detection and index diagnostics into operator-grade maintenance workflows that can repair vault defects after user confirmation.

Tasks:

- [x] Add index freshness diagnostics via `index info`.
- [x] Detect exact duplicate Markdown groups by content hash.
- [x] Choose a canonical path for exact duplicates and surface it in `inspect`.
- [x] Canonicalize exact duplicates in `related`.
- [x] Canonicalize exact duplicates in `synthesis suggest`.
- [x] Document duplicate handling rules in operator docs.
- [x] Add a dedicated `duplicates list` command for duplicate clusters.
- [x] Add `duplicates inspect <path-or-group>` with canonical recommendation and overlap explanation.
- [x] Distinguish exact duplicates from semantic duplicates in CLI output and maintenance workflows.
- [x] Add a first `maintenance report` command and shared finding model for vault defect diagnostics.
- [x] Surface meaningful empty directories using ignore rules plus role/structure semantics.
- [x] Aggregate exact duplicate clusters and stale synthesis notes into the shared maintenance report layer.
- [x] Expand vault defect reports to summarize ambiguous links, missing links, and unconfigured structure profiles in the same layer.
- [ ] Add confirm-driven link-rewrite and source-note cleanup workflows for exact duplicate clusters.
- [ ] Add synthesis-first reconciliation workflow for semantic duplicates before any merge/delete proposal.
- [ ] Add Python-first `maintenance plan/apply` architecture with bounded action types and explicit confirmation.
- [ ] Keep LLM usage advisory-only for ambiguous link resolution, semantic reconciliation, and synthesis refresh decisions.
- [ ] Add maintenance write logging for canonicalization and cleanup operations.

Exit criteria:

- Brainiac can explain current vault defects without broad manual inspection.
- Exact duplicates can be canonicalized consistently before future writes.
- Semantic duplicates can be reconciled through synthesis before source-note cleanup.
- Maintenance workflows are confirm-driven and auditable.

Planned commands:

```bash
PYTHONPATH=src python3 -m brainiac duplicates list
PYTHONPATH=src python3 -m brainiac duplicates inspect <path-or-group>
PYTHONPATH=src python3 -m brainiac maintenance report
PYTHONPATH=src python3 -m brainiac maintenance plan <finding-id>
PYTHONPATH=src python3 -m brainiac maintenance apply <plan-id> --confirm
```

Apply architecture:

- Python should detect, classify, diff, validate, plan, apply, and log all maintenance operations.
- LLM should only interpret ambiguous cases, compare semantic overlaps, propose reconciliation, or draft synthesis refreshes.
- LLM should not execute vault writes directly; confirmed file operations should be applied by Python from a bounded action model.
- Expected low-risk Python-first actions: delete empty files/directories, rewrite exact-duplicate links, remove non-canonical exact-duplicate copies, refresh index-backed metadata.
- Expected hybrid actions: ambiguous wikilink resolution, semantic duplicate reconciliation, synthesis refresh/update.
- The intended action model should stay explicit and auditable, for example `RewriteWikilinkAction`, `DeleteFileAction`, `DeleteDirectoryAction`, and `UpdateSynthesisAction`.

Current boundary:

- implemented: detect exact duplicates, surface canonical paths, canonicalize exact duplicates for retrieval and synthesis, list exact duplicate clusters, inspect canonical reasons, separate semantic duplicate ideas from exact groups, and report empty directories, exact duplicate clusters, stale synthesis notes, missing/ambiguous wikilinks, and unconfigured structure profiles through a shared maintenance finding model
- not yet implemented: confirm-driven relink, cleanup/apply workflows, Python-first maintenance execution, semantic-duplicate reconciliation workflows, and maintenance writes

## Phase 6: First Real Workflow

Goal: prove usefulness on one low-risk domain.

Candidate domains:

- food;
- 3D printing;
- book highlights;
- travel ideas.

Tasks:

- [ ] Pick one domain.
- [ ] Process existing notes in that domain.
- [ ] Generate one synthesis note.
- [ ] Generate one HTML dashboard or report.
- [ ] Try routing 5 new items.
- [ ] Record what worked and what failed.

Exit criteria:

- Brainiac produces a result the user would actually reuse.

## Phase 7: Optional Semantic Search

Goal: add embeddings only after structural/lexical retrieval proves useful.

Tasks:

- [ ] Choose embedding provider/model.
- [ ] Track embedding model version.
- [ ] Chunk by sections, not only full files.
- [ ] Store vectors in SQLite extension or a small local vector store.
- [ ] Combine semantic results with structural ranking.
- [ ] Add reindex behavior for model changes.

Exit criteria:

- Semantic search improves retrieval quality enough to justify the added complexity.

## Phase 8: MCP or Local Service

Goal: expose Brainiac as a proper AI tool backend.

Tasks:

- [ ] Decide MCP vs local HTTP vs CLI-first.
- [ ] Wrap stable commands as tools.
- [ ] Add safe write operations.
- [ ] Add operation logs.
- [ ] Add policy checks for sensitive domains.

Exit criteria:

- Jarvis can use Brainiac as a tool provider.

## Phase 9: Obsidian Integration

Goal: make Brainiac convenient inside Obsidian without depending on Obsidian as the backend.

Tasks:

- [ ] Evaluate Local REST API vs custom plugin.
- [ ] Add command to open generated dashboards.
- [ ] Optionally read Obsidian metadata cache.
- [ ] Add "route current note" workflow.
- [ ] Add "show related notes" workflow.

Exit criteria:

- Brainiac improves the Obsidian experience without becoming an Obsidian-only system.

## Phase 10: Maintenance Automation

Goal: automate upkeep only after synthesis, retrieval, routing, and safe writes are proven manually.

Maintenance should build on Phase 5 synthesis primitives instead of introducing a separate understanding layer.

Tasks:

- [ ] Add scheduled or explicit maintenance reports for stale synthesis notes.
- [ ] Detect contradictions between synthesis notes and changed raw sources.
- [ ] Detect orphan/generated artifacts that are stale or unsupported by current sources.
- [ ] Detect notes that should probably update an existing synthesis note.
- [ ] Detect areas/projects with many raw captures but no synthesis note.
- [ ] Add dry-run maintenance plans with explicit source references.
- [ ] Add policy gates for applying maintenance changes.
- [ ] Add optional notification/report output, but avoid daily briefing spam.

Exit criteria:

- Brainiac can keep synthesis and generated outputs fresh without silently rewriting source-of-truth notes.
