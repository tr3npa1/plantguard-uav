"""Establish the empty PlantGuard schema baseline.

Revision ID: 0001_schema_baseline
Revises:
Create Date: 2026-08-20
"""

from collections.abc import Sequence

revision: str = "0001_schema_baseline"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Establish the baseline without creating application tables."""


def downgrade() -> None:
    """Return to the pre-baseline schema without dropping application data."""
