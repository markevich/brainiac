# External Source Takeaways

The user provided several internet posts/articles as context. These notes are takeaways, not accepted truth. The project should treat them critically.

## HTML vs Markdown

Relevant takeaway:

- Markdown is still best for long-lived, editable, searchable, AI-readable source material.
- HTML is useful for human-facing generated artifacts: visual explainers, dashboards, comparison grids, interactive prototypes, and reports.
- The useful pattern is one canonical source with generated HTML views, not duplicated source content across formats.

Decision for Brainiac:

```text
Markdown/structured files = source of truth
HTML = generated presentation layer
```

Avoid:

- HTML as default durable memory;
- HTML files with embedded source-only content that cannot be cleanly extracted;
- generated HTML that directly mutates the vault.

## Obsidian as Business Operating System

Repeated article pattern:

- use Obsidian/plain Markdown as a local vault;
- add an operator through filesystem/MCP;
- maintain predictable folders like inbox, projects, areas, resources, daily, generated, queue, archive;
- use a master instruction file;
- automate research, briefings, weekly reviews, project status, client briefs, etc.

Useful ideas:

- `inbox` for low-friction capture;
- `queue` for explicit work requests;
- `generated` for AI outputs that are not source of truth;
- operation logs;
- folder conventions designed for agents, not only humans;
- review gates for communications/deletes/commitments.

Critical stance:

- direct full-vault write access is risky;
- autonomous daily/weekly generation can become noise;
- weekly rewriting of core agent rules can cause instruction drift;
- folder structure is not a replacement for retrieval;
- automation should come after indexing and routing work reliably.

Decision for Brainiac:

Start with retrieval and controlled writes. Add automations later.

## Passive Capture and Context Debt

Article pattern:

- capture friction kills knowledge systems;
- bookmarks, highlights, voice notes, videos, and articles should land in an inbox automatically;
- AI should process new captures into memory.

Useful idea:

- Brainiac should eventually support passive ingest.

Critical stance:

- automatic ingest without synthesis/routing creates a bigger junk drawer;
- raw captures should remain raw sources;
- processing should produce reviewable suggestions or synthesis, not silent rewrites.

Decision for Brainiac:

Capture is a future workflow. First build inventory, routing, and retrieval.

## RAG vs LLM Wiki

Article pattern:

- basic RAG retrieves chunks but does not preserve understanding;
- an LLM Wiki maintains persistent synthesized knowledge;
- new documents update concept pages, entity pages, contradictions, comparisons, and open questions.

Useful idea:

- Brainiac needs both retrieval and synthesis.

Important distinction:

```text
retrieval index = what is relevant now?
synthesis notes = what have we already concluded over time?
```

Decision for Brainiac:

Maintain synthesis notes as Markdown first. Tie each synthesis back to raw source files.

## Freshman Rule / Accuracy Over Ego

Article pattern:

- require source citations for important claims;
- plan before acting;
- stop when new info contradicts old notes;
- avoid assuming when vault evidence is missing.

Useful idea:

- Brainiac should return source paths and snippets.
- Sensitive domains require citations and confirmation.
- Contradictions should be surfaced, not smoothed over.

Decision for Brainiac:

Tool responses should include `why`, `source`, and confidence-like signals where possible.

## What Brainiac Should Not Copy Blindly

- "Give the agent keys to everything" as a default.
- Autonomous overnight rewriting of core instructions.
- Treating generated briefings as proof the system is learning.
- Over-indexing before there is a real retrieval workflow.
- Assuming embeddings alone solve organization.
