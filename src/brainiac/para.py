from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .bootstrap import PARA_DIRECTORIES


CANONICAL_ROOTS = {
    "inbox": "Inbox/",
    "project": "Projects/",
    "area": "Areas/",
    "resource": "Resources/",
    "archive": "Archive/",
}


@dataclass(frozen=True)
class ParaViolation:
    type: str
    path: str
    summary: str
    suggested_action: str


def validate_para_layout(vault_root: Path) -> tuple[ParaViolation, ...]:
    """Return canonical PARA directory violations without changing the vault."""
    root = vault_root.expanduser().resolve()
    return tuple(
        ParaViolation(
            type="missing_para_directory",
            path=f"{relative_path}/",
            summary="Missing required PARA directory",
            suggested_action=f"Create `{relative_path}/` or restore it before routing new notes.",
        )
        for relative_path in PARA_DIRECTORIES
        if not (root / relative_path).is_dir()
    )


def require_para_layout(vault_root: Path | None) -> None:
    if vault_root is None:
        raise ValueError("Vault root is not configured for this PARA-managed vault.")
    violations = validate_para_layout(vault_root)
    if not violations:
        return
    details = "; ".join(f"{item.type}: {item.path}" for item in violations)
    raise ValueError(f"PARA layout is not compliant; route is blocked. {details}")
