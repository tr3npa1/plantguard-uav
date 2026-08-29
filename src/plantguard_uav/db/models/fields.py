"""Database representation of the current saved-field selection projection."""

from typing import Any

from sqlalchemy import CheckConstraint, JSON, PrimaryKeyConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column

from plantguard_uav.db.base import Base


class SavedFieldDefinitionRow(Base):
    """Store one current field-sector definition as validated JSON components."""

    __tablename__ = "saved_field_definitions"
    __table_args__ = (
        PrimaryKeyConstraint(
            "field_id",
            "sector_id",
            name="pk_saved_field_definitions",
        ),
        CheckConstraint(
            "length(trim(field_id)) > 0",
            name="ck_saved_field_definitions_field_id_nonblank",
        ),
        CheckConstraint(
            "length(trim(sector_id)) > 0",
            name="ck_saved_field_definitions_sector_id_nonblank",
        ),
        CheckConstraint(
            "length(trim(field_name)) > 0",
            name="ck_saved_field_definitions_field_name_nonblank",
        ),
        CheckConstraint(
            "length(trim(crop_type)) > 0",
            name="ck_saved_field_definitions_crop_type_nonblank",
        ),
        CheckConstraint(
            "length(trim(field_version)) > 0",
            name="ck_saved_field_definitions_field_version_nonblank",
        ),
        CheckConstraint(
            "schema_version = '1.0'",
            name="ck_saved_field_definitions_schema_version_supported",
        ),
    )

    field_id: Mapped[str] = mapped_column(Text, nullable=False)
    sector_id: Mapped[str] = mapped_column(Text, nullable=False)
    field_name: Mapped[str] = mapped_column(Text, nullable=False)
    crop_type: Mapped[str] = mapped_column(Text, nullable=False)
    field_boundary: Mapped[dict[str, Any]] = mapped_column(
        JSON(none_as_null=True),
        nullable=False,
    )
    sector_boundary: Mapped[dict[str, Any]] = mapped_column(
        JSON(none_as_null=True),
        nullable=False,
    )
    home_location: Mapped[dict[str, Any]] = mapped_column(
        JSON(none_as_null=True),
        nullable=False,
    )
    exclusion_zones: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON(none_as_null=True),
        nullable=False,
    )
    field_version: Mapped[str] = mapped_column(Text, nullable=False)
    schema_version: Mapped[str] = mapped_column(Text, nullable=False)
