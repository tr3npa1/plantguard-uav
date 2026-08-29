from io import StringIO
from pathlib import Path
import sqlite3
from typing import NoReturn

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import URL

from plantguard_uav.db import SCHEMA_HEAD, Base

pytestmark = pytest.mark.integration


def _migration_config(project_root: Path, database_path: Path) -> Config:
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "migrations"))
    database_url = URL.create(
        "sqlite+aiosqlite",
        database=str(database_path.resolve()),
    ).render_as_string(hide_password=False)
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def _current_revision(database_path: Path) -> str | None:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    return None if row is None else str(row[0])


def _application_tables(database_path: Path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    return {str(row[0]) for row in rows} - {"alembic_version"}


def test_declared_schema_head_matches_alembic_head(project_root: Path) -> None:
    config = Config(str(project_root / "alembic.ini"))
    script = ScriptDirectory.from_config(config)

    assert script.get_current_head() == SCHEMA_HEAD


def test_offline_upgrade_generates_sql_without_connecting(
    project_root: Path,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "offline-migration.sqlite3"
    config = _migration_config(project_root, database_path)
    output = StringIO()
    config.output_buffer = output

    command.upgrade(config, "head", sql=True)

    generated_sql = output.getvalue()
    assert "CREATE TABLE alembic_version" in generated_sql
    assert "CREATE TABLE saved_field_definitions" in generated_sql
    assert "PRIMARY KEY (field_id, sector_id)" in generated_sql
    assert "schema_version = '1.0'" in generated_sql
    assert SCHEMA_HEAD in generated_sql
    assert not database_path.exists()


def test_upgrade_downgrade_upgrade_cycle_uses_alembic_only(
    project_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    private_url_fragment = "private-database-token"
    database_path = tmp_path / f"{private_url_fragment}.sqlite3"
    config = _migration_config(project_root, database_path)

    def reject_create_all(*args: object, **kwargs: object) -> NoReturn:
        del args, kwargs
        raise AssertionError("Migrations must not call Base.metadata.create_all().")

    monkeypatch.setattr(Base.metadata, "create_all", reject_create_all)

    command.upgrade(config, "head")
    assert _current_revision(database_path) == SCHEMA_HEAD
    assert _application_tables(database_path) == {"saved_field_definitions"}

    with sqlite3.connect(database_path) as connection:
        columns = connection.execute("PRAGMA table_info(saved_field_definitions)").fetchall()
        table_sql_row = connection.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type = 'table' AND name = 'saved_field_definitions'"
        ).fetchone()

    assert [str(column[1]) for column in columns] == [
        "field_id",
        "sector_id",
        "field_name",
        "crop_type",
        "field_boundary",
        "sector_boundary",
        "home_location",
        "exclusion_zones",
        "field_version",
        "schema_version",
    ]
    assert all(int(column[3]) == 1 for column in columns)
    assert [int(column[5]) for column in columns[:2]] == [1, 2]
    assert all(int(column[5]) == 0 for column in columns[2:])
    assert table_sql_row is not None
    table_sql = str(table_sql_row[0])
    assert "ck_saved_field_definitions_schema_version_supported" in table_sql
    assert "schema_version = '1.0'" in table_sql

    captured = capsys.readouterr()
    assert private_url_fragment not in captured.out
    assert private_url_fragment not in captured.err

    command.downgrade(config, "base")
    assert _current_revision(database_path) is None
    assert _application_tables(database_path) == set()

    command.upgrade(config, "head")
    assert _current_revision(database_path) == SCHEMA_HEAD
    assert _application_tables(database_path) == {"saved_field_definitions"}
