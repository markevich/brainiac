# Phase 4 Structure Notes

New Brainiac-managed vaults use the canonical PARA roots: `Inbox/`,
`Projects/`, `Areas/`, `Resources/`, and `Archive/`. Tool-owned state stays
outside the vault.

`brainiac structure` reads the SQLite index and derives profiles from those
paths. It does not scan or modify the vault. A profile reports its role, path,
note and file counts, common tags and terms, and representative notes.

`brainiac route` uses the same indexed paths as candidates. It scores lexical
evidence with document-frequency weighting, requires at least two shared
specific terms in a supporting note, and prefers deeper supported folders. If
the evidence is weak, it proposes `Inbox/`; it never guesses a topical folder
just because of one generic match. Exact title/note-name collisions are shown
separately from topical evidence.

PARA profiles are the only routing model. They need no separate routing map to
keep paths in sync.
