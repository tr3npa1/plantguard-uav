from typing import cast

from sqlalchemy import JSON, CheckConstraint, PrimaryKeyConstraint, Table, Text

from plantguard_uav.db import Base, SavedFieldDefinitionRow


def test_saved_field_model_registers_the_expected_table_and_columns() -> None:
    table = cast(Table, SavedFieldDefinitionRow.__table__)

    assert Base.metadata.tables["saved_field_definitions"] is table
    assert tuple(table.columns) == (
        table.c.field_id,
        table.c.sector_id,
        table.c.field_name,
        table.c.crop_type,
        table.c.field_boundary,
        table.c.sector_boundary,
        table.c.home_location,
        table.c.exclusion_zones,
        table.c.field_version,
        table.c.schema_version,
    )
    assert all(column.nullable is False for column in table.columns)


def test_saved_field_model_uses_a_composite_primary_key() -> None:
    table = cast(Table, SavedFieldDefinitionRow.__table__)
    primary_key = next(
        constraint
        for constraint in table.constraints
        if isinstance(constraint, PrimaryKeyConstraint)
    )

    assert primary_key.name == "pk_saved_field_definitions"
    assert tuple(primary_key.columns) == (table.c.field_id, table.c.sector_id)


def test_saved_field_model_uses_text_for_required_scalar_values() -> None:
    table = cast(Table, SavedFieldDefinitionRow.__table__)

    for column_name in (
        "field_id",
        "sector_id",
        "field_name",
        "crop_type",
        "field_version",
        "schema_version",
    ):
        assert isinstance(table.c[column_name].type, Text)


def test_saved_field_model_stores_geometries_as_non_null_json() -> None:
    table = cast(Table, SavedFieldDefinitionRow.__table__)

    for column_name in (
        "field_boundary",
        "sector_boundary",
        "home_location",
        "exclusion_zones",
    ):
        json_type = table.c[column_name].type
        assert isinstance(json_type, JSON)
        assert json_type.none_as_null is True


def test_saved_field_model_declares_named_portable_integrity_checks() -> None:
    table = cast(Table, SavedFieldDefinitionRow.__table__)
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert checks == {
        "ck_saved_field_definitions_crop_type_nonblank": "length(trim(crop_type)) > 0",
        "ck_saved_field_definitions_field_id_nonblank": "length(trim(field_id)) > 0",
        "ck_saved_field_definitions_field_name_nonblank": "length(trim(field_name)) > 0",
        "ck_saved_field_definitions_field_version_nonblank": ("length(trim(field_version)) > 0"),
        "ck_saved_field_definitions_schema_version_supported": "schema_version = '1.0'",
        "ck_saved_field_definitions_sector_id_nonblank": "length(trim(sector_id)) > 0",
    }
