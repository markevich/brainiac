# Brainiac Operator Playbook

## Startup

1. Read local vault, routing, and policy configs.
2. Run `brainiac index info` and, when current state matters, `brainiac index info --check-filesystem`.
3. Scan only if the index is missing or drift matters to the task.

## Retrieval

Use `search`, `inspect`, `related`, and then `read` selected files. Do not search the whole vault directly until bounded retrieval is insufficient.

## Source and umbrella rule

New notes are `source` by default. An umbrella is an explicit navigation note that links sources and can contain brief selection guidance.

After a material source update, use `inspect` to find umbrella backlinks. Propose an update only when the source changes what the umbrella should help a person find or choose. A shared folder, common word, or two related notes is not enough to create an umbrella.

## Maintenance

Use `maintenance report` for empty directories, exact duplicates, links, roles, structure, and semantic overlaps. Preserve uncertain overlaps; do not silently merge or delete notes.
