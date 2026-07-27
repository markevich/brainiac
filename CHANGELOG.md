# Brainiac Changelog

Detailed upgrade entries live in small version-range files so an LLM reads only the migrations it needs.

## Files

- `changelog/01-02.md`

## Rules

Each version entry with a non-`none` migration contains:

- **What changed** — a user-facing summary.
- **Verification** — how to detect that the migration target already exists.
- **Migration** — exact idempotent steps for an existing local Brainiac installation, or `none`.
- **Validation** — how to prove the final state.

When `brainiac.md` changes version, add the corresponding changelog entry in the same commit.
