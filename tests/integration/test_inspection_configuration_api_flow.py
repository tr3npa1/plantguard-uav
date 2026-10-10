"""Exercise HTTP configuration reads through the real source, service, and bounded loader."""

from collections.abc import Iterator
from dataclasses import dataclass
import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from plantguard_uav.adapters import inspection_configuration as adapter
from plantguard_uav.config import Settings
from plantguard_uav.db import DatabaseRuntime
from plantguard_uav.domain.inspection_configuration import InspectionFlightConfiguration
from plantguard_uav.main import create_app

pytestmark = pytest.mark.integration

_ENDPOINT = "/api/v1/inspection-configuration"
_CONFIGURATION_ID = "synthetic-http-configuration"
_VERSION = "synthetic-revision-a"
_CONFIGURATION_ERROR = {
    "error": {
        "code": "configuration_error",
        "message": "Inspection configuration could not be loaded.",
    },
}


def _synthetic_content(*, version: str = _VERSION, survey_speed: float = 3.0) -> bytes:
    # These numbers exercise validation; they are not approved operational settings.
    return json.dumps(
        {
            "configuration_id": _CONFIGURATION_ID,
            "configuration_version": version,
            "operating_environment": "nominal_dry_daylight",
            "survey": {
                "altitude_agl_m": 12,
                "speed_m_s": survey_speed,
                "front_overlap_fraction": 0.5,
                "side_overlap_fraction": 0.25,
            },
            "revisit": {"altitude_agl_m": 6, "speed_m_s": 4},
        },
    ).encode("utf-8")


def _params(*, version: str = _VERSION) -> dict[str, str]:
    return {"configuration_id": _CONFIGURATION_ID, "configuration_version": version}


@dataclass(frozen=True)
class _ConfigurationApi:
    client: TestClient
    path: Path
    original_content: bytes


@pytest.fixture
def configuration_api(
    tmp_path: Path,
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[_ConfigurationApi]:
    path = tmp_path / "private-selected-configuration.json"
    content = _synthetic_content()
    path.write_bytes(content)

    def forbid_database_transaction() -> None:
        raise AssertionError("Configuration reads must not open database transactions.")

    monkeypatch.setattr(database_runtime, "transaction", forbid_database_transaction)
    source = adapter.FileInspectionConfigurationSource(path)
    app = create_app(
        test_settings,
        database_runtime=database_runtime,
        inspection_configuration_source=source,
    )
    with TestClient(app) as client:
        yield _ConfigurationApi(client=client, path=path, original_content=content)


def test_http_returns_complete_configuration_without_modifying_source_or_creating_database(
    configuration_api: _ConfigurationApi,
) -> None:
    expected = InspectionFlightConfiguration.model_validate_json(configuration_api.original_content)
    original_entries = set(configuration_api.path.parent.iterdir())

    response = configuration_api.client.get(_ENDPOINT, params=_params())

    assert response.status_code == 200
    assert response.json() == expected.model_dump(mode="json")
    assert response.headers["content-type"] == "application/json"
    assert response.headers["cache-control"] == "no-store"
    assert configuration_api.path.read_bytes() == configuration_api.original_content
    assert set(configuration_api.path.parent.iterdir()) == original_entries


def test_http_reads_current_contents_with_same_identity_without_claiming_a_snapshot(
    configuration_api: _ConfigurationApi,
) -> None:
    first = configuration_api.client.get(_ENDPOINT, params=_params())
    replacement = _synthetic_content(survey_speed=2.0)
    configuration_api.path.write_bytes(replacement)

    second = configuration_api.client.get(_ENDPOINT, params=_params())

    assert first.status_code == second.status_code == 200
    for identifier in ("configuration_id", "configuration_version"):
        assert first.json()[identifier] == second.json()[identifier]
    assert first.json()["survey"]["speed_m_s"] == 3.0
    assert second.json()["survey"]["speed_m_s"] == 2.0
    assert first.headers["cache-control"] == second.headers["cache-control"] == "no-store"
    assert configuration_api.path.read_bytes() == replacement


def test_http_rechecks_revision_after_file_replacement(
    configuration_api: _ConfigurationApi,
) -> None:
    first = configuration_api.client.get(_ENDPOINT, params=_params())
    replacement = _synthetic_content(version="synthetic-revision-b")
    configuration_api.path.write_bytes(replacement)

    stale_request = configuration_api.client.get(_ENDPOINT, params=_params())
    current_request = configuration_api.client.get(
        _ENDPOINT, params=_params(version="synthetic-revision-b")
    )

    assert first.status_code == 200
    assert stale_request.status_code == 500
    assert stale_request.json() == _CONFIGURATION_ERROR
    assert stale_request.headers["cache-control"] == "no-store"
    assert current_request.status_code == 200
    assert current_request.json()["configuration_version"] == "synthetic-revision-b"
    assert current_request.headers["cache-control"] == "no-store"
    assert configuration_api.path.read_bytes() == replacement


@pytest.mark.parametrize(
    "replacement",
    [
        pytest.param(b"private-malformed-document", id="malformed-json"),
        pytest.param(b'{"private-duplicate": 1, "private-duplicate": 2}', id="duplicate-key"),
        pytest.param(b'{"private-number": NaN}', id="nonfinite-constant"),
        pytest.param(b'{"private-number": 1e400}', id="overflowing-number"),
        pytest.param(b" " * (adapter.MAX_INSPECTION_CONFIGURATION_BYTES + 1), id="oversized"),
        pytest.param(b"\xffprivate-invalid-encoding", id="invalid-encoding"),
        pytest.param(_synthetic_content(survey_speed=-1), id="invalid-domain-value"),
    ],
)
def test_http_rejects_corrupt_replacement_without_returning_stale_success_or_private_data(
    configuration_api: _ConfigurationApi,
    replacement: bytes,
) -> None:
    first = configuration_api.client.get(_ENDPOINT, params=_params())
    assert first.status_code == 200
    configuration_api.path.write_bytes(replacement)

    response = configuration_api.client.get(_ENDPOINT, params=_params())

    assert response.status_code == 500
    assert response.json() == _CONFIGURATION_ERROR
    assert response.headers["cache-control"] == "no-store"
    assert "private-" not in response.text
    assert str(configuration_api.path) not in response.text
    assert configuration_api.path.read_bytes() == replacement


def test_http_returns_failure_after_file_deletion_and_recovers_when_file_is_restored(
    configuration_api: _ConfigurationApi,
) -> None:
    first = configuration_api.client.get(_ENDPOINT, params=_params())
    configuration_api.path.unlink()

    missing = configuration_api.client.get(_ENDPOINT, params=_params())

    assert first.status_code == 200
    assert missing.status_code == 500
    assert missing.json() == _CONFIGURATION_ERROR
    assert missing.headers["cache-control"] == "no-store"
    assert not configuration_api.path.exists()
    configuration_api.path.write_bytes(configuration_api.original_content)

    restored = configuration_api.client.get(_ENDPOINT, params=_params())

    assert restored.status_code == 200
    assert restored.json() == first.json()
    assert restored.headers["cache-control"] == "no-store"


def test_http_rejects_directory_replacement_without_stale_success(
    configuration_api: _ConfigurationApi,
) -> None:
    first = configuration_api.client.get(_ENDPOINT, params=_params())
    configuration_api.path.unlink()
    configuration_api.path.mkdir()

    response = configuration_api.client.get(_ENDPOINT, params=_params())

    assert first.status_code == 200
    assert response.status_code == 500
    assert response.json() == _CONFIGURATION_ERROR
    assert response.headers["cache-control"] == "no-store"
    assert list(configuration_api.path.iterdir()) == []


def test_http_query_parameters_and_environment_cannot_select_a_different_file(
    configuration_api: _ConfigurationApi,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alternate_path = configuration_api.path.parent / "private-alternate.json"
    alternate_content = _synthetic_content(survey_speed=2.0)
    alternate_path.write_bytes(alternate_content)
    monkeypatch.setenv("PLANTGUARD_INSPECTION_CONFIGURATION_PATH", str(alternate_path))
    params = {**_params(), "path": str(alternate_path), "configuration_path": str(alternate_path)}

    response = configuration_api.client.get(_ENDPOINT, params=params)
    path_as_id = configuration_api.client.get(
        _ENDPOINT, params={**_params(), "configuration_id": str(alternate_path)}
    )

    assert response.status_code == 200
    assert response.json()["survey"]["speed_m_s"] == 3.0
    assert path_as_id.status_code == 500
    assert path_as_id.json() == _CONFIGURATION_ERROR
    assert path_as_id.headers["cache-control"] == "no-store"
    assert configuration_api.path.read_bytes() == configuration_api.original_content
    assert alternate_path.read_bytes() == alternate_content


def test_missing_selected_file_has_no_environment_or_working_directory_fallback(
    configuration_api: _ConfigurationApi,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fallback_path = configuration_api.path.parent / "inspection_configuration.json"
    fallback_path.write_bytes(configuration_api.original_content)
    configuration_api.path.unlink()
    monkeypatch.chdir(configuration_api.path.parent)
    monkeypatch.setenv("PLANTGUARD_INSPECTION_CONFIGURATION_PATH", str(fallback_path))

    response = configuration_api.client.get(_ENDPOINT, params=_params())

    assert response.status_code == 500
    assert response.json() == _CONFIGURATION_ERROR
    assert response.headers["cache-control"] == "no-store"
    assert not configuration_api.path.exists()
    assert fallback_path.read_bytes() == configuration_api.original_content


def test_application_defers_real_file_loading_until_a_valid_request(
    tmp_path: Path,
    test_settings: Settings,
    database_runtime: DatabaseRuntime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected_path = tmp_path / "private-not-created.json"
    loaded_paths: list[Path] = []
    actual_loader = adapter.load_inspection_configuration

    def traced_loader(path: Path) -> InspectionFlightConfiguration:
        loaded_paths.append(path)
        return actual_loader(path)

    monkeypatch.setattr(adapter, "load_inspection_configuration", traced_loader)
    source = adapter.FileInspectionConfigurationSource(selected_path)
    app = create_app(
        test_settings,
        database_runtime=database_runtime,
        inspection_configuration_source=source,
    )
    assert loaded_paths == []

    with TestClient(app) as client:
        assert loaded_paths == []
        invalid = client.get(_ENDPOINT, params={"configuration_id": _CONFIGURATION_ID})
        assert invalid.status_code == 422
        assert invalid.headers["cache-control"] == "no-store"
        assert loaded_paths == []

        response = client.get(_ENDPOINT, params=_params())

        assert response.status_code == 500
        assert response.json() == _CONFIGURATION_ERROR
        assert response.headers["cache-control"] == "no-store"
        assert loaded_paths == [selected_path]

    assert loaded_paths == [selected_path]
    assert not selected_path.exists()
