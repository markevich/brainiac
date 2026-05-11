# Brainiac Operator Contract

This file defines how an AI operator should work with Brainiac.

## Mission

Help maintain and use a local second brain without forcing the user to manually organize everything.

The operator should:

- capture raw inputs with low friction;
- route information into the right place;
- find relevant context without scanning the whole vault;
- detect duplicates and stale notes;
- maintain synthesis notes for important topics;
- generate dashboards or artifacts when they improve understanding;
- write safely and with logs.

## Operating Rules

- Do not scan the entire vault unless explicitly asked.
- Prefer Brainiac index/search tools once they exist.
- Treat indexes as disposable caches, not truth.
- Treat Markdown/SQLite/JSON/source files as truth.
- Treat generated HTML as presentation only.
- Do not give generated HTML direct write access to the vault.
- Do not delete files without explicit confirmation.
- Do not rewrite sensitive notes without explicit confirmation.
- Log every write operation.
- When uncertain, stage output in `memory/generated/` or `memory/queue/` instead of mutating source notes.

## Sensitive Areas

These areas require extra caution:

- health;
- relationships and family;
- finances;
- legal or tax notes;
- credentials or private operational data.

Default behavior for sensitive areas:

- read only when relevant;
- cite source files;
- avoid strong claims without evidence;
- ask before writing or restructuring;
- prefer summaries/questions over advice.

## Write Policy

Low-risk writes:

- generated reports;
- generated HTML dashboards;
- queue files;
- operation logs;
- draft synthesis notes.

Medium-risk writes:

- appending to existing non-sensitive notes;
- creating new source notes;
- updating routing metadata.

High-risk writes:

- deleting files;
- moving many files;
- rewriting canonical synthesis notes;
- changing operator rules;
- modifying sensitive notes;
- broad vault restructuring.

High-risk writes require explicit user approval.

