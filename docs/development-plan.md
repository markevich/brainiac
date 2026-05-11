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

- `scan` explicitly rebuilds the disposable SQLite index from source files.
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
```

Implementation notes:

- `scan` creates a searchable FTS5 table from Markdown path, title, headings, tags, tasks, and body text.
- `search` reads the existing index only; it does not rescan the vault.
- `inspect` returns bounded metadata: file facts, headings, tags, tasks, outgoing links, backlinks, and ambiguous-link warnings.
- `read` returns a whole file or a single Markdown heading section with a max-character budget.
- `related` combines outgoing links, backlinks, preferred ambiguous-link candidates, shared tags, same-folder proximity, and title/heading lexical overlap.
- Ambiguous wikilinks keep all candidates and a deterministic preferred path. This is a best-effort Obsidian-compatible guess, not a guarantee of Obsidian's internal resolver.
- Generic task tags such as `#todo/now` are intentionally weak relatedness signals so they do not dominate explicit links.
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
- [ ] Separate universal roles from user-specific paths: inbox, projects, areas, resources, archive, generated, synthesis, queue.
- [ ] Add routing config schema for roles, aliases, sensitive domains, important short tokens, and domain-specific hints.
- [ ] Define a high-level vault map index over roles, areas, projects, resources, and synthesis roots.
- [ ] Generate compact area/project profiles from existing notes: title, path, role, tags, top terms, representative notes, recent activity, sensitive flag, and short human-readable summary.
- [ ] Use the vault map as the first routing layer: rank candidate areas/projects by profile before selecting a destination note.
- [ ] Treat manual hints as optional local overrides, not as the primary multilingual routing strategy.
- [ ] Support empty or sparse vaults with generic role templates and "candidate new area" suggestions.
- [ ] Add a command or report that diagnoses a vault's structure against the recommended model.
- [ ] Document migration-safe recommendations: suggest, do not move files automatically.
- [ ] Revisit Phase 3 scoring once role metadata exists, so routing is not over-dependent on folder names.

Exit criteria:

- Brainiac can explain what role each configured vault path plays.
- Routing rules can be portable across vaults by role, while local paths remain config-only.
- No source code contains user-specific vault path assumptions.
- Routing decisions can be made from compact area/project profiles instead of hardcoded multilingual keyword dictionaries.

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

- [ ] Define synthesis note format: current stance, key points, decisions, open questions, contradictions, sources, last reviewed.
- [ ] Define frontmatter or metadata convention for synthesis notes.
- [ ] Add synthesis roots to config and index them as a distinct role/type.
- [ ] Track source references from synthesis notes to raw notes.
- [ ] Track source hash/mtime snapshots used by each synthesis note.
- [ ] Implement `synthesis list`.
- [ ] Implement `synthesis inspect <topic-or-path>`.
- [ ] Implement `synthesis stale` to detect synthesis notes whose sources changed.
- [ ] Implement `synthesis suggest <topic-or-path>` as dry-run only.
- [ ] Make `search` and `related` surface relevant synthesis notes before raw sources when appropriate.
- [ ] Add review-before-apply policy for synthesis writes.
- [ ] Document that synthesis is derived memory, not raw evidence.

Exit criteria:

- Brainiac can preserve conclusions over time instead of making Jarvis re-synthesize everything on each query.
- Jarvis can use a synthesis note as the first context layer for a topic.
- Brainiac can explain which raw sources support a synthesis note and whether that synthesis may be stale.

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
