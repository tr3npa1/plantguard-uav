from inspect import Parameter, signature

from pydantic import ValidationError
import pytest

from plantguard_uav.domain.field import MAX_FIELD_PAGE_OFFSET, SavedFieldSummary
from plantguard_uav.errors import PersistenceError
from plantguard_uav.repositories.fields import FieldCatalogueRepository
from plantguard_uav.services.field_catalogue import ListSavedFieldsQuery, ListSavedFieldsService


class FakeFieldCatalogueRepository:
    def __init__(self, results: list[tuple[SavedFieldSummary, ...]]) -> None:
        self._results = results.copy()
        self.calls: list[tuple[int, int]] = []

    async def list_summaries(self, *, limit: int, offset: int) -> tuple[SavedFieldSummary, ...]:
        self.calls.append((limit, offset))
        return self._results.pop(0)


class FailingFieldCatalogueRepository:
    def __init__(self, error: PersistenceError) -> None:
        self._error = error

    async def list_summaries(self, *, limit: int, offset: int) -> tuple[SavedFieldSummary, ...]:
        del limit, offset
        raise self._error


def _summary(
    *, sector_id: str = "sector_01", field_version: str = "version_01"
) -> SavedFieldSummary:
    return SavedFieldSummary(
        field_id="field_01",
        sector_id=sector_id,
        field_name="North Field",
        crop_type="Wheat",
        field_version=field_version,
    )


def _set_attribute(instance: object, attribute: str, value: object) -> None:
    setattr(instance, attribute, value)


def test_catalogue_query_defaults_are_frozen_and_internal() -> None:
    query = ListSavedFieldsQuery()

    assert query.model_dump(mode="json") == {"limit": 20, "offset": 0}
    with pytest.raises(ValidationError, match="frozen"):
        _set_attribute(query, "limit", 50)


@pytest.mark.parametrize(
    ("limit", "offset"),
    [(1, 0), (20, 1), (100, MAX_FIELD_PAGE_OFFSET)],
)
def test_catalogue_query_accepts_inclusive_pagination_bounds(limit: int, offset: int) -> None:
    query = ListSavedFieldsQuery(limit=limit, offset=offset)

    assert query.limit == limit
    assert query.offset == offset


@pytest.mark.parametrize(
    "values",
    [
        {"limit": 0},
        {"limit": -1},
        {"limit": 101},
        {"limit": True},
        {"limit": 20.0},
        {"limit": "20"},
        {"limit": None},
        {"offset": -1},
        {"offset": MAX_FIELD_PAGE_OFFSET + 1},
        {"offset": 10**100},
        {"offset": False},
        {"offset": 0.0},
        {"offset": "0"},
        {"offset": None},
        {"schema_version": "1.0"},
        {"unexpected": True},
    ],
)
def test_catalogue_query_rejects_invalid_bounds_types_and_extra_fields(
    values: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ListSavedFieldsQuery.model_validate(values)


def test_catalogue_query_copy_revalidates_without_changing_original() -> None:
    query = ListSavedFieldsQuery()

    copied = query.model_copy(update={"limit": 100, "offset": 40})

    assert copied.model_dump(mode="json") == {"limit": 100, "offset": 40}
    assert query.model_dump(mode="json") == {"limit": 20, "offset": 0}
    with pytest.raises(ValidationError):
        query.model_copy(update={"offset": MAX_FIELD_PAGE_OFFSET + 1})


def test_catalogue_repository_protocol_requires_keyword_only_pagination() -> None:
    method_parameters = signature(FieldCatalogueRepository.list_summaries).parameters

    assert tuple(method_parameters) == ("self", "limit", "offset")
    assert method_parameters["limit"].kind is Parameter.KEYWORD_ONLY
    assert method_parameters["offset"].kind is Parameter.KEYWORD_ONLY


async def test_catalogue_service_returns_an_empty_page_using_default_lookahead() -> None:
    fake = FakeFieldCatalogueRepository([()])
    repository: FieldCatalogueRepository = fake
    service = ListSavedFieldsService(repository)

    page = await service.execute(ListSavedFieldsQuery())

    assert page.model_dump(mode="json") == {
        "items": [],
        "limit": 20,
        "offset": 0,
        "has_more": False,
        "schema_version": "1.0",
    }
    assert fake.calls == [(21, 0)]


@pytest.mark.parametrize(
    ("row_count", "has_more"),
    [(0, False), (1, False), (2, False), (3, True)],
)
async def test_catalogue_service_returns_only_requested_items_and_uses_extra_row_for_more_flag(
    row_count: int,
    has_more: bool,
) -> None:
    rows = tuple(_summary(sector_id=f"sector_{index:02d}") for index in range(row_count))
    original_rows = tuple(row.model_dump(round_trip=True) for row in rows)
    fake = FakeFieldCatalogueRepository([rows])
    service = ListSavedFieldsService(fake)

    page = await service.execute(ListSavedFieldsQuery(limit=2, offset=7))

    assert page.items == rows[:2]
    assert page.limit == 2
    assert page.offset == 7
    assert page.has_more is has_more
    assert fake.calls == [(3, 7)]
    assert tuple(row.model_dump(round_trip=True) for row in rows) == original_rows


async def test_catalogue_service_permits_101_row_lookahead_for_the_maximum_page_size() -> None:
    rows = tuple(_summary(sector_id=f"sector_{index:03d}") for index in range(101))
    fake = FakeFieldCatalogueRepository([rows])
    service = ListSavedFieldsService(fake)

    page = await service.execute(ListSavedFieldsQuery(limit=100, offset=MAX_FIELD_PAGE_OFFSET))

    assert page.items == rows[:100]
    assert page.has_more is True
    assert page.offset == MAX_FIELD_PAGE_OFFSET
    assert fake.calls == [(101, MAX_FIELD_PAGE_OFFSET)]


async def test_catalogue_service_retains_repository_order_without_mutating_summaries() -> None:
    rows = (_summary(sector_id="sector_z"), _summary(sector_id="sector_a"))
    original_rows = tuple(row.model_dump(round_trip=True) for row in rows)
    fake = FakeFieldCatalogueRepository([rows])
    service = ListSavedFieldsService(fake)

    page = await service.execute(ListSavedFieldsQuery(limit=2))

    assert tuple(item.sector_id for item in page.items) == ("sector_z", "sector_a")
    assert tuple(row.model_dump(round_trip=True) for row in rows) == original_rows


async def test_catalogue_service_performs_a_fresh_repository_read_for_every_request() -> None:
    first = _summary(field_version="version_01")
    changed = _summary(field_version="version_02")
    fake = FakeFieldCatalogueRepository([(first,), (changed,)])
    service = ListSavedFieldsService(fake)
    query = ListSavedFieldsQuery(limit=1, offset=4)

    first_page = await service.execute(query)
    second_page = await service.execute(query)

    assert first_page.items == (first,)
    assert second_page.items == (changed,)
    assert second_page.items[0].field_version == "version_02"
    assert fake.calls == [(2, 4), (2, 4)]


async def test_catalogue_service_propagates_persistence_failures_unchanged() -> None:
    original_error = PersistenceError(context={"operation": "list_saved_fields"})
    service = ListSavedFieldsService(FailingFieldCatalogueRepository(original_error))

    with pytest.raises(PersistenceError) as caught:
        await service.execute(ListSavedFieldsQuery())

    assert caught.value is original_error
