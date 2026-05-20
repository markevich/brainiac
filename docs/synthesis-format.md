# Synthesis Note Format

Synthesis notes are derived memory. They summarize current understanding, but raw Markdown, structured files, and other source artifacts remain the evidence.

## Location

Synthesis notes can be discovered in either way:

- placed under a configured `synthesis_roots` path in `config/routing.yml`;
- marked with frontmatter `brainiac_role: synthesis`.

Recommended naming:

- use a stable `.synthesis.md` suffix for new synthesis notes so they stay out of the ordinary source-note basename namespace.

## Frontmatter

Recommended minimal frontmatter:

```yaml
---
brainiac_role: synthesis
topic: Example topic
last_reviewed: 2026-05-11
source_snapshots:
  - "Sources/Raw note.md|source-sha256|source-mtime"
---
```

`source_snapshots` is optional. When present, Brainiac compares the stored SHA-256 with the current indexed source hash and reports stale synthesis notes.

Lifecycle rule:

- source notes change first;
- `synthesis stale` reports the affected synthesis note;
- a refresh or rewrite brings the synthesis note back in sync;
- semantic duplicate detection is for source/source overlap, not source/synthesis freshness drift.

## Body

Recommended sections:

```markdown
# Example topic

## Current stance

## Key points

## Decisions

## Contradictions

## Open questions

## Sources
```

Sources should use normal Obsidian wikilinks, for example `[[Sources/Raw note]]`. Brainiac resolves those links through the index and treats them as evidence references.

## Read-only Commands

```bash
PYTHONPATH=src python3 -m brainiac synthesis list
PYTHONPATH=src python3 -m brainiac synthesis inspect "Example topic"
PYTHONPATH=src python3 -m brainiac synthesis stale
PYTHONPATH=src python3 -m brainiac synthesis suggest "Example topic"
```

These commands do not write to the vault. `suggest` prints a candidate path, source list, and draft Markdown that can be reviewed before any later write workflow exists.

## Write Policy

Synthesis notes are derived memory, so synthesis writes must use review-before-apply:

- `synthesis suggest` is allowed as dry-run output.
- Future synthesis write commands must require explicit confirmation.
- Future synthesis write commands must include source links and source snapshots.
- Sensitive source domains still require their normal sensitive-write review.
