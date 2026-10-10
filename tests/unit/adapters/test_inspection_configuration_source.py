"""Exercise source wiring with synthetic inputs, never approved flight settings."""

import json
from pathlib import Path

import pytest

from plantguard_uav.adapters import inspection_configuration as adapter
from plantguard_uav.domain.inspection_configuration import InspectionFlightConfiguration
from plantguard_uav.errors import (
    InspectionConfigurationError,
    InspectionConfigurationFailureReason,
)
from plantguard_uav.services.inspection_configuration import (
    GetInspectionConfigurationQuery,
    GetInspectionConfigurationService,
)


def _synthetic_content(
    *, version: str = "synthetic-revision-a", survey_speed: float = 3.0
) -> bytes:
    return json.dumps(
        {
            "configuration_id": "synthetic-source-test",
            "configuration_version": version,
            "operating_environment": "nominal_dry_daylight",
            "survey": {
                "altitude_agl_m": 12,
                "speed_m_s": survey_speed,
                "front_overlap_fraction": 0.5,
                "side_overlap_fraction": 0.25,
            },
            "revisit": {"altitude_agl_m": 6, "speed_m_s": 4},
        }
    ).encode("utf-8")


def _query(*, version: str = "synthetic-revision-a") -> GetInspectionConfigurationQuery:
    return GetInspectionConfigurationQuery(
        configuration_id="synthetic-source-test", configuration_version=version
    )


def _assert_reason(error: InspectionConfigurationError, reason: str) -> None:
    assert error.public_message == "Inspection configuration could not be loaded."
    assert error.context == {"operation": "load_inspection_configuration", "reason": reason}


def test_source_construction_does_not_load_or_access_filesystem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected_path = tmp_path / "not-created.json"

    def forbid_io(*args: object, **kwargs: object) -> None:
        raise AssertionError("Constructing a source must not perform I/O.")

    with monkeypatch.context() as scoped:
        scoped.setattr(adapter, "load_inspection_configuration", forbid_io)
        scoped.setattr(Path, "stat", forbid_io)
        scoped.setattr(Path, "open", forbid_io)
        adapter.FileInspectionConfigurationSource(selected_path)

    assert not selected_path.exists()


def test_source_delegates_every_load_using_the_exact_explicit_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected_path = Path("explicit-parent") / ".." / "selected.json"
    first = adapter.parse_inspection_configuration_json(_synthetic_content())
    second = adapter.parse_inspection_configuration_json(
        _synthetic_content(version="synthetic-revision-b")
    )
    results = [first, second]
    received_paths: list[Path] = []

    def load_selected(path: Path) -> InspectionFlightConfiguration:
        received_paths.append(path)
        return results.pop(0)

    monkeypatch.setattr(adapter, "load_inspection_configuration", load_selected)
    source = adapter.FileInspectionConfigurationSource(selected_path)

    assert source.load() is first
    assert source.load() is second
    assert received_paths == [selected_path, selected_path]
    assert all(path is selected_path for path in received_paths)


@pytest.mark.parametrize("reason", ["file_unavailable", "invalid_json", "invalid_configuration"])
def test_source_preserves_controlled_loader_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reason: InspectionConfigurationFailureReason,
) -> None:
    error = InspectionConfigurationError(reason=reason)

    def fail_load(path: Path) -> InspectionFlightConfiguration:
        raise error

    monkeypatch.setattr(adapter, "load_inspection_configuration", fail_load)
    source = adapter.FileInspectionConfigurationSource(tmp_path / "selected.json")

    with pytest.raises(InspectionConfigurationError) as captured:
        source.load()

    assert captured.value is error
    _assert_reason(captured.value, reason)


def test_source_reads_validated_configuration_without_changing_file(tmp_path: Path) -> None:
    selected_path = tmp_path / "selected.json"
    content = _synthetic_content()
    selected_path.write_bytes(content)
    source = adapter.FileInspectionConfigurationSource(selected_path)

    configuration = source.load()

    assert isinstance(configuration, InspectionFlightConfiguration)
    assert configuration == InspectionFlightConfiguration.model_validate_json(content)
    assert selected_path.read_bytes() == content
    assert list(tmp_path.iterdir()) == [selected_path]


def test_source_reads_current_file_instead_of_caching_prior_configuration(tmp_path: Path) -> None:
    selected_path = tmp_path / "selected.json"
    selected_path.write_bytes(_synthetic_content())
    source = adapter.FileInspectionConfigurationSource(selected_path)
    first = source.load()
    replacement = _synthetic_content(version="synthetic-revision-b")
    selected_path.write_bytes(replacement)

    second = source.load()

    assert first.configuration_version == "synthetic-revision-a"
    assert second.configuration_version == "synthetic-revision-b"
    assert second is not first
    assert selected_path.read_bytes() == replacement


def test_source_does_not_return_stale_success_after_selected_file_is_removed(
    tmp_path: Path,
) -> None:
    selected_path = tmp_path / "selected.json"
    selected_path.write_bytes(_synthetic_content())
    source = adapter.FileInspectionConfigurationSource(selected_path)
    source.load()
    selected_path.unlink()

    with pytest.raises(InspectionConfigurationError) as captured:
        source.load()

    _assert_reason(captured.value, "file_unavailable")
    assert not selected_path.exists()


def test_source_ignores_environment_overrides_for_selected_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected_path = tmp_path / "selected.json"
    selected_path.write_bytes(_synthetic_content())
    alternative_path = tmp_path / "environment.json"
    alternative_path.write_bytes(_synthetic_content(version="synthetic-revision-b"))
    monkeypatch.setenv("PLANTGUARD_INSPECTION_CONFIGURATION_PATH", str(alternative_path))
    monkeypatch.setenv("PLANTGUARD_CONFIGURATION_VERSION", "synthetic-revision-b")

    configuration = adapter.FileInspectionConfigurationSource(selected_path).load()

    assert configuration.configuration_version == "synthetic-revision-a"


def test_source_does_not_discover_a_fallback_when_selected_file_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fallback_path = tmp_path / "inspection_configuration.json"
    fallback_path.write_bytes(_synthetic_content())
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PLANTGUARD_INSPECTION_CONFIGURATION_PATH", str(fallback_path))
    selected_path = tmp_path / "missing.json"
    source = adapter.FileInspectionConfigurationSource(selected_path)

    with pytest.raises(InspectionConfigurationError) as captured:
        source.load()

    _assert_reason(captured.value, "file_unavailable")
    assert fallback_path.read_bytes() == _synthetic_content()
    assert not selected_path.exists()


def test_real_file_source_and_service_return_matching_identity(tmp_path: Path) -> None:
    selected_path = tmp_path / "selected.json"
    content = _synthetic_content()
    selected_path.write_bytes(content)
    service = GetInspectionConfigurationService(
        adapter.FileInspectionConfigurationSource(selected_path)
    )

    configuration = service.execute(_query())

    assert configuration.configuration_id == "synthetic-source-test"
    assert configuration.configuration_version == "synthetic-revision-a"
    assert configuration.survey.speed_m_s == 3.0
    assert selected_path.read_bytes() == content


def test_service_rechecks_identity_after_the_selected_file_changes_revision(tmp_path: Path) -> None:
    selected_path = tmp_path / "selected.json"
    selected_path.write_bytes(_synthetic_content())
    service = GetInspectionConfigurationService(
        adapter.FileInspectionConfigurationSource(selected_path)
    )
    first = service.execute(_query())
    replacement = _synthetic_content(version="synthetic-revision-b")
    selected_path.write_bytes(replacement)

    with pytest.raises(InspectionConfigurationError) as captured:
        service.execute(_query())

    _assert_reason(captured.value, "identity_mismatch")
    second = service.execute(_query(version="synthetic-revision-b"))
    assert first.configuration_version == "synthetic-revision-a"
    assert second.configuration_version == "synthetic-revision-b"
    assert selected_path.read_bytes() == replacement


def test_service_observes_content_changes_with_same_identity_without_claiming_snapshot(
    tmp_path: Path,
) -> None:
    selected_path = tmp_path / "selected.json"
    selected_path.write_bytes(_synthetic_content())
    service = GetInspectionConfigurationService(
        adapter.FileInspectionConfigurationSource(selected_path)
    )
    first = service.execute(_query())
    replacement = _synthetic_content(survey_speed=2.0)
    selected_path.write_bytes(replacement)

    second = service.execute(_query())

    assert first.configuration_id == second.configuration_id
    assert first.configuration_version == second.configuration_version
    assert first.survey.speed_m_s == 3.0
    assert second.survey.speed_m_s == 2.0
    assert selected_path.read_bytes() == replacement


def test_service_rejects_corrupt_replacement_instead_of_returning_stale_success(
    tmp_path: Path,
) -> None:
    selected_path = tmp_path / "selected.json"
    selected_path.write_bytes(_synthetic_content())
    service = GetInspectionConfigurationService(
        adapter.FileInspectionConfigurationSource(selected_path)
    )
    service.execute(_query())
    replacement = b"{"
    selected_path.write_bytes(replacement)

    with pytest.raises(InspectionConfigurationError) as captured:
        service.execute(_query())

    _assert_reason(captured.value, "invalid_json")
    assert selected_path.read_bytes() == replacement


def test_source_can_load_after_an_earlier_failure_is_corrected(tmp_path: Path) -> None:
    selected_path = tmp_path / "selected.json"
    source = adapter.FileInspectionConfigurationSource(selected_path)
    with pytest.raises(InspectionConfigurationError):
        source.load()
    selected_path.write_bytes(_synthetic_content())

    configuration = source.load()

    assert configuration.configuration_id == "synthetic-source-test"
