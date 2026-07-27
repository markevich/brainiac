# Brainiac Upgrade Flow

Use this file only after the user approved a Git update, or when `brainiac.md` has a higher version than `installed_version` in `brainiac_me.md`.

## Order

1. Read the installed version from `brainiac_me.md` and the target version from `brainiac.md`.
2. Read `CHANGELOG.md`, then only the `changelog/*.md` files overlapping the version range.
3. Process every version in ascending order.
4. For each `### Migration`, run its verification first. If the target state is
   already present, record it as complete for this attempt and do not repeat
   the change.
5. For incomplete work, explain the intended local changes and ask for
   confirmation before changing files.
6. Back up every file that an incomplete migration will change under
   `.state/backups/`.
7. Run the migration's stated validation immediately after its changes.
8. Update `installed_version` in `brainiac_me.md` only after every migration
   and validation succeeds.

The `installed_version` is the completion marker. Migrations must be
idempotent: their verification detects already-completed work and their
validation proves the intended state. If an upgrade fails, leave
`installed_version` unchanged, keep backups, explain the failed step, and
restart the ordered checks safely on the next session.

## Rules

- Do not infer user choices during a migration.
- Do not move or rewrite vault notes as part of a Brainiac installation upgrade.
- If a version has no migration, record `none` in its changelog entry.
- Every non-`none` migration must define **Verification**, **Migration**, and
  **Validation**. Its operations must be safe to rerun after a partial failure.
