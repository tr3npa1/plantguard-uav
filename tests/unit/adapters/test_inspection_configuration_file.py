"""Exercise file loading with synthetic inputs, never approved flight settings."""

import json
import os
from pathlib import Path
import stat
from types import TracebackType
from typing import BinaryIO, Self

import pytest

from plantguard_uav.adapters import inspection_configuration as adapter
from plantguard_uav.domain.inspection_configuration import InspectionFlightConfiguration
from plantguard_uav.errors import ConfigurationError, InspectionConfigurationError


def _synthetic_content(*, version: str = "synthetic-revision-a") -> bytes:
    return json.dumps(
        {
            "configuration_id": "synthetic-configuration",
            "configuration_version": version,
            "operating_environment": "nominal_dry_daylight",
            "survey": {
                "altitude_agl_m": 12,
                "speed_m_s": 3,
                "front_overlap_fraction": 0.5,
                "side_overlap_fraction": 0.25,
            },
            "revisit": {"altitude_agl_m": 6, "speed_m_s": 4},
        }
    ).encode("utf-8")


class _TrackedFile:
    def __init__(
        self,
        handle: BinaryIO,
        *,
        content: bytes | None = None,
        read_error: OSError | None = None,
    ) -> None:
        self.handle = handle
        self.content = content
        self.read_error = read_error
        self.read_sizes: list[int] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.handle.close()

    def fileno(self) -> int:
        return self.handle.fileno()

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        if self.read_error is not None:
            raise self.read_error
        if self.content is not None:
            return self.content[:size] if size >= 0 else self.content
        return self.handle.read(size)


def _track_open(
    monkeypatch: pytest.MonkeyPatch,
    source: Path,
    *,
    content: bytes | None = None,
    read_error: OSError | None = None,
) -> _TrackedFile:
    tracked = _TrackedFile(source.open("rb"), content=content, read_error=read_error)

    def open_tracked(path: Path, mode: str = "r") -> _TrackedFile:
        assert path == source
        assert mode == "rb"
        return tracked

    monkeypatch.setattr(Path, "open", open_tracked)
    return tracked


def _assert_safe_error(error: InspectionConfigurationError, reason: str) -> None:
    assert isinstance(error, ConfigurationError)
    assert error.error_code == "configuration_error"
    assert error.public_message == "Inspection configuration could not be loaded."
    assert str(error) == error.public_message
    assert error.context == {"operation": "load_inspection_configuration", "reason": reason}


def test_loads_explicit_file_without_changing_source_bytes(tmp_path: Path) -> None:
    source = tmp_path / "synthetic-inspection.json"
    content = _synthetic_content()
    source.write_bytes(content)

    loaded = adapter.load_inspection_configuration(source)

    assert loaded == InspectionFlightConfiguration.model_validate_json(content)
    assert source.read_bytes() == content
    assert list(tmp_path.iterdir()) == [source]


def test_each_load_reads_current_contents_without_cached_configuration(tmp_path: Path) -> None:
    source = tmp_path / "synthetic-inspection.json"
    source.write_bytes(_synthetic_content())
    original = adapter.load_inspection_configuration(source)
    source.write_bytes(_synthetic_content(version="synthetic-revision-b"))

    updated = adapter.load_inspection_configuration(source)

    assert original.configuration_version == "synthetic-revision-a"
    assert updated.configuration_version == "synthetic-revision-b"
    assert updated is not original
    assert source.read_bytes() == _synthetic_content(version="synthetic-revision-b")


@pytest.mark.parametrize("relative_name", ["missing.json", "missing-parent/missing.json"])
def test_missing_file_is_a_safe_error(tmp_path: Path, relative_name: str) -> None:
    source = tmp_path / relative_name

    with pytest.raises(InspectionConfigurationError) as captured:
        adapter.load_inspection_configuration(source)

    _assert_safe_error(captured.value, "file_unavailable")
    assert not source.exists()


def test_directory_is_rejected_before_open(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbid_open(path: Path, mode: str = "r") -> None:
        raise AssertionError("A directory must never reach file opening.")

    monkeypatch.setattr(Path, "open", forbid_open)

    with pytest.raises(InspectionConfigurationError) as captured:
        adapter.load_inspection_configuration(tmp_path)

    _assert_safe_error(captured.value, "not_regular_file")


@pytest.mark.parametrize("file_mode", [stat.S_IFIFO, stat.S_IFCHR, stat.S_IFSOCK])
def test_special_file_is_rejected_before_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, file_mode: int
) -> None:
    source = tmp_path / "synthetic-special"

    def special_stat(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        return os.stat_result((file_mode, 0, 0, 1, 0, 0, 0, 0, 0, 0))

    def forbid_open(path: Path, mode: str = "r") -> None:
        raise AssertionError("A special file must never reach file opening.")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "stat", special_stat)
        scoped.setattr(Path, "open", forbid_open)
        with pytest.raises(InspectionConfigurationError) as captured:
            adapter.load_inspection_configuration(source)

    _assert_safe_error(captured.value, "not_regular_file")


@pytest.mark.parametrize("failure", [PermissionError("private-source"), OSError("private-source")])
def test_stat_failures_are_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: OSError
) -> None:
    source = tmp_path / "private-source.json"

    def fail_stat(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        raise failure

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "stat", fail_stat)
        with pytest.raises(InspectionConfigurationError) as captured:
            adapter.load_inspection_configuration(source)

    _assert_safe_error(captured.value, "file_unavailable")


def test_invalid_path_is_a_safe_error(tmp_path: Path) -> None:
    with pytest.raises(InspectionConfigurationError) as captured:
        adapter.load_inspection_configuration(tmp_path / "private\x00source.json")

    _assert_safe_error(captured.value, "file_unavailable")


@pytest.mark.parametrize("failure", [PermissionError("private-source"), OSError("private-source")])
def test_open_failures_are_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: OSError
) -> None:
    source = tmp_path / "private-source.json"
    source.write_bytes(_synthetic_content())

    def fail_open(path: Path, mode: str = "r") -> BinaryIO:
        raise failure

    monkeypatch.setattr(Path, "open", fail_open)
    with pytest.raises(InspectionConfigurationError) as captured:
        adapter.load_inspection_configuration(source)

    _assert_safe_error(captured.value, "file_unavailable")


def test_read_failure_closes_file_and_is_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "private-source.json"
    source.write_bytes(_synthetic_content())
    tracked = _track_open(monkeypatch, source, read_error=OSError("private-read-failure"))

    with pytest.raises(InspectionConfigurationError) as captured:
        adapter.load_inspection_configuration(source)

    _assert_safe_error(captured.value, "file_unavailable")
    assert tracked.handle.closed
    assert tracked.read_sizes == [adapter.MAX_INSPECTION_CONFIGURATION_BYTES + 1]


@pytest.mark.parametrize("content", [_synthetic_content(), b"{"])
def test_file_is_closed_after_success_or_parse_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: bytes
) -> None:
    source = tmp_path / "synthetic-inspection.json"
    source.write_bytes(content)
    tracked = _track_open(monkeypatch, source)

    if content == b"{":
        with pytest.raises(InspectionConfigurationError) as captured:
            adapter.load_inspection_configuration(source)
        _assert_safe_error(captured.value, "invalid_json")
    else:
        loaded = adapter.load_inspection_configuration(source)
        assert loaded.configuration_id == "synthetic-configuration"

    assert tracked.handle.closed
    assert tracked.read_sizes == [adapter.MAX_INSPECTION_CONFIGURATION_BYTES + 1]


def test_actual_read_is_bounded_when_file_grows_after_stat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "synthetic-inspection.json"
    source.write_bytes(_synthetic_content())
    grown_content = b" " * (adapter.MAX_INSPECTION_CONFIGURATION_BYTES + 100)
    tracked = _track_open(monkeypatch, source, content=grown_content)

    with pytest.raises(InspectionConfigurationError) as captured:
        adapter.load_inspection_configuration(source)

    _assert_safe_error(captured.value, "input_too_large")
    assert tracked.read_sizes == [adapter.MAX_INSPECTION_CONFIGURATION_BYTES + 1]
    assert tracked.handle.closed


def test_opened_file_is_checked_again_before_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "synthetic-inspection.json"
    source.write_bytes(_synthetic_content())
    tracked = _track_open(monkeypatch, source)

    def special_fstat(file_descriptor: int) -> os.stat_result:
        assert file_descriptor == tracked.handle.fileno()
        return os.stat_result((stat.S_IFCHR, 0, 0, 1, 0, 0, 0, 0, 0, 0))

    monkeypatch.setattr(os, "fstat", special_fstat)
    with pytest.raises(InspectionConfigurationError) as captured:
        adapter.load_inspection_configuration(source)

    _assert_safe_error(captured.value, "not_regular_file")
    assert tracked.read_sizes == []
    assert tracked.handle.closed


def test_opened_file_stat_failure_closes_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "synthetic-inspection.json"
    source.write_bytes(_synthetic_content())
    tracked = _track_open(monkeypatch, source)

    def fail_fstat(file_descriptor: int) -> os.stat_result:
        raise OSError("private-handle-failure")

    monkeypatch.setattr(os, "fstat", fail_fstat)
    with pytest.raises(InspectionConfigurationError) as captured:
        adapter.load_inspection_configuration(source)

    _assert_safe_error(captured.value, "file_unavailable")
    assert tracked.read_sizes == []
    assert tracked.handle.closed


def test_file_exactly_at_size_limit_is_accepted(tmp_path: Path) -> None:
    content = _synthetic_content()
    padded = content + b" " * (adapter.MAX_INSPECTION_CONFIGURATION_BYTES - len(content))
    source = tmp_path / "synthetic-inspection.json"
    source.write_bytes(padded)

    loaded = adapter.load_inspection_configuration(source)

    assert loaded.configuration_id == "synthetic-configuration"
    assert source.read_bytes() == padded


def test_oversized_file_fails_without_changing_source(tmp_path: Path) -> None:
    content = b" " * (adapter.MAX_INSPECTION_CONFIGURATION_BYTES + 1)
    source = tmp_path / "synthetic-inspection.json"
    source.write_bytes(content)

    with pytest.raises(InspectionConfigurationError) as captured:
        adapter.load_inspection_configuration(source)

    _assert_safe_error(captured.value, "input_too_large")
    assert source.read_bytes() == content


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        (b"\xffprivate-input", "invalid_encoding"),
        (b"private-input", "invalid_json"),
        (b'{"private-input":1,"private-input":2}', "duplicate_key"),
        (b'{"private-input":NaN}', "nonfinite_number"),
        (b'{"configuration_id":"private-input"}', "invalid_configuration"),
    ],
)
def test_file_content_failures_remain_safe_and_leave_file_unchanged(
    tmp_path: Path, content: bytes, reason: str
) -> None:
    source = tmp_path / "private-source.json"
    source.write_bytes(content)

    with pytest.raises(InspectionConfigurationError) as captured:
        adapter.load_inspection_configuration(source)

    _assert_safe_error(captured.value, reason)
    public_and_context = f"{captured.value!s} {captured.value.context!r}"
    assert "private-input" not in public_and_context
    assert str(source) not in public_and_context
    assert source.read_bytes() == content


def test_environment_does_not_override_explicit_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "synthetic-inspection.json"
    source.write_bytes(_synthetic_content())
    monkeypatch.setenv("PLANTGUARD_CONFIGURATION_VERSION", "unexpected-environment-value")
    monkeypatch.setenv("PLANTGUARD_INSPECTION_CONFIGURATION_PATH", str(tmp_path / "missing.json"))

    loaded = adapter.load_inspection_configuration(source)

    assert loaded.configuration_version == "synthetic-revision-a"


def test_no_fallback_when_selected_file_is_missing(tmp_path: Path) -> None:
    default_profile = tmp_path / "inspection_configuration.json"
    default_profile.write_bytes(_synthetic_content())

    with pytest.raises(InspectionConfigurationError) as captured:
        adapter.load_inspection_configuration(tmp_path / "missing.json")

    _assert_safe_error(captured.value, "file_unavailable")
    assert default_profile.read_bytes() == _synthetic_content()
