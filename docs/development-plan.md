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

- [ ] Define routing rules in `config/routing.yml`.
- [ ] Implement `route(content)` returning candidate destinations and reasons.
- [ ] Implement `find_duplicates(content)` using lexical similarity and metadata.
- [ ] Add dry-run write suggestions.
- [ ] Add note-name collision checks before any proposed create/write operation.
- [ ] Define unique-title generation for Brainiac-created notes.
- [ ] Generate links in a shortest-unique format so Brainiac-created links do not introduce ambiguity.
- [ ] Add write log format.

Exit criteria:

- Given a new note or inbox item, Brainiac can suggest where it belongs and what existing notes may overlap.
- Brainiac does not propose creating Markdown notes or links that introduce duplicate basename ambiguity.

## Phase 4: First Real Workflow

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

## Phase 5: Optional Semantic Search

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

## Phase 6: MCP or Local Service

Goal: expose Brainiac as a proper AI tool backend.

Tasks:

- [ ] Decide MCP vs local HTTP vs CLI-first.
- [ ] Wrap stable commands as tools.
- [ ] Add safe write operations.
- [ ] Add operation logs.
- [ ] Add policy checks for sensitive domains.

Exit criteria:

- Jarvis can use Brainiac as a tool provider.

## Phase 7: Obsidian Integration

Goal: make Brainiac convenient inside Obsidian without depending on Obsidian as the backend.

Tasks:

- [ ] Evaluate Local REST API vs custom plugin.
- [ ] Add command to open generated dashboards.
- [ ] Optionally read Obsidian metadata cache.
- [ ] Add "route current note" workflow.
- [ ] Add "show related notes" workflow.

Exit criteria:

- Brainiac improves the Obsidian experience without becoming an Obsidian-only system.

## Phase 8: Synthesis and Maintenance

Goal: move beyond search into persistent understanding.

Tasks:

- [ ] Define synthesis note format.
- [ ] Implement "suggest synthesis update" as dry-run.
- [ ] Track raw sources referenced by synthesis notes.
- [ ] Detect contradictions or stale summaries.
- [ ] Add review-before-apply policy for important synthesis.

Exit criteria:

- Brainiac can preserve conclusions over time instead of making the AI re-synthesize everything on each query.
