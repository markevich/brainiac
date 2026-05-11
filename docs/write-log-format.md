# Brainiac Write Log Format

Brainiac write operations must be explicit, policy-checked, and logged. The log is append-only JSON Lines stored under:

```text
memory/logs/operations.jsonl
```

Each line is one JSON object with this shape:

```json
{
  "schema_version": 1,
  "operation_id": "2026-05-11T10:20:30.123456Z-create-note-example",
  "created_at": "2026-05-11T10:20:30.123456Z",
  "actor": "jarvis",
  "command": "create_note",
  "dry_run": false,
  "policy": {
    "decision": "allowed",
    "matched_rules": ["explicit_user_request"]
  },
  "target": {
    "vault_relative_path": "2_Areas/Food/Fermentation.md",
    "content_type": "markdown"
  },
  "inputs": {
    "source": "cli",
    "source_paths": [],
    "reason": "Route captured note into existing food area."
  },
  "changes": {
    "action": "create",
    "before_sha256": null,
    "after_sha256": "sha256-hex",
    "summary": "Created note with routed capture content."
  }
}
```

Required fields:

- `schema_version`: integer log schema version.
- `operation_id`: stable unique ID for the operation.
- `created_at`: UTC ISO-8601 timestamp.
- `actor`: operator identity, usually `jarvis`.
- `command`: write command name.
- `dry_run`: whether the operation only proposed changes.
- `policy.decision`: `allowed`, `blocked`, or `review_required`.
- `target.vault_relative_path`: affected vault path.
- `changes.action`: `create`, `update`, `move`, `delete`, or `append`.
- `changes.before_sha256`: previous file hash, or `null` for creates.
- `changes.after_sha256`: new file hash, or `null` for deletes and dry-runs.
- `changes.summary`: compact human-readable description.

Rules:

- Dry-run suggestions may be logged, but real writes must always be logged.
- Sensitive-domain writes must use `policy.decision = "review_required"` unless the user explicitly approves the mutation.
- Logs are metadata and audit trail only. Markdown, SQLite, JSON, YAML, CSV, and source assets remain the source of truth.
