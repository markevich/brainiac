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

Tasks:

- [ ] Build a CLI command that scans a vault path.
- [ ] Collect files, paths, sizes, mtimes, hashes, and empty-note status.
- [ ] Extract Markdown headings.
- [ ] Extract wikilinks and unresolved links.
- [ ] Extract tags.
- [ ] Extract Markdown tasks.
- [ ] Write results to SQLite.
- [ ] Generate a simple text or HTML inventory report.

Exit criteria:

- Brainiac can answer "what is in this vault?" without reading all files into AI context.

## Phase 2: Bounded Search and Inspect

Goal: give the AI useful retrieval tools before adding embeddings.

Tasks:

- [ ] Implement lexical search over titles, headings, paths, tags, and text snippets.
- [ ] Implement `inspect(path)` for metadata, headings, links, backlinks, tasks.
- [ ] Implement `read(path, section?)`.
- [ ] Implement `related(path)` using links, backlinks, folder proximity, tags, and lexical overlap.
- [ ] Enforce result limits and snippet budgets.

Exit criteria:

- The AI can find relevant notes and read selected sections without scanning the whole vault.

## Phase 3: Routing and Dedupe

Goal: help place new information into the vault.

Tasks:

- [ ] Define routing rules in `config/routing.yml`.
- [ ] Implement `route(content)` returning candidate destinations and reasons.
- [ ] Implement `find_duplicates(content)` using lexical similarity and metadata.
- [ ] Add dry-run write suggestions.
- [ ] Add write log format.

Exit criteria:

- Given a new note or inbox item, Brainiac can suggest where it belongs and what existing notes may overlap.

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
