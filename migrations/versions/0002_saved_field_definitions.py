"""Create the current saved-field selection projection.

Revision ID: 0002_saved_field_definitions
Revises: 0001_schema_baseline
Create Date: 2026-08-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_saved_field_definitions"
down_revision: str | Sequence[str] | None = "0001_schema_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the saved-field table without inserting application data."""
    op.create_table(
        "saved_field_definitions",
        sa.Column("field_id", sa.Text(), nullable=False),
        sa.Column("sector_id", sa.Text(), nullable=False),
        sa.Column("field_name", sa.Text(), nullable=False),
        sa.Column("crop_type", sa.Text(), nullable=False),
        sa.Column("field_boundary", sa.JSON(none_as_null=True), nullable=False),
        sa.Column("sector_boundary", sa.JSON(none_as_null=True), nullable=False),
        sa.Column("home_location", sa.JSON(none_as_null=True), nullable=False),
        sa.Column("exclusion_zones", sa.JSON(none_as_null=True), nullable=False),
        sa.Column("field_version", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint(
            "field_id",
            "sector_id",
            name="pk_saved_field_definitions",
        ),
        sa.CheckConstraint(
            "length(trim(field_id)) > 0",
            name="ck_saved_field_definitions_field_id_nonblank",
        ),
        sa.CheckConstraint(
            "length(trim(sector_id)) > 0",
            name="ck_saved_field_definitions_sector_id_nonblank",
        ),
        sa.CheckConstraint(
            "length(trim(field_name)) > 0",
            name="ck_saved_field_definitions_field_name_nonblank",
        ),
        sa.CheckConstraint(
            "length(trim(crop_type)) > 0",
            name="ck_saved_field_definitions_crop_type_nonblank",
        ),
        sa.CheckConstraint(
            "length(trim(field_version)) > 0",
            name="ck_saved_field_definitions_field_version_nonblank",
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'",
            name="ck_saved_field_definitions_schema_version_supported",
        ),
    )


def downgrade() -> None:
    """Remove only the saved-field selection projection table."""
    op.drop_table("saved_field_definitions")
