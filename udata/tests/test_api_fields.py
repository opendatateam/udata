import factory
import mongoengine
import pytest
from flask_restx.reqparse import Argument, RequestParser

from udata.api_fields import field, function_field, generate_fields, patch, patch_and_save
from udata.core.dataset.api_fields import dataset_fields
from udata.core.organization import constants as org_constants
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Organization
from udata.core.owned import Owned
from udata.core.storages import default_image_basename, images
from udata.factories import ModelFactory
from udata.models import Badge, BadgeMixin, BadgesList, WithMetrics, db
from udata.mongo.queryset import DBPaginator, UDataQuerySet
from udata.utils import faker

pytestmark = [
    pytest.mark.usefixtures("clean_db"),
]

BIGGEST_IMAGE_SIZE: int = 500

BADGES: dict[str, str] = {
    "badge-1": "badge 1",
    "badge-2": "badge 2",
}

URL_RAISE_ERROR: str = "/raise/validation/error"
URL_EXISTS_ERROR_MESSAGE: str = "Url exists"


def check_url(url: str = "", **_kwargs) -> None:
    if url == URL_RAISE_ERROR:
        raise ValueError(URL_EXISTS_ERROR_MESSAGE)
    return


class FakeBadge(Badge):
    kind = db.StringField(required=True, choices=list(BADGES.keys()))


class FakeBadgeMixin(BadgeMixin):
    badges = field(BadgesList(FakeBadge), **BadgeMixin.default_badges_list_params)
    __badges__ = BADGES


@generate_fields(
    searchable=True,
    additional_sorts=[
        {"key": "datasets", "value": "metrics.datasets"},
        {"key": "followers", "value": "metrics.followers"},
        {"key": "views", "value": "metrics.views"},
    ],
    additional_filters={"organization_badge": "organization.badges"},
)
class Fake(WithMetrics, FakeBadgeMixin, Owned, db.Document):
    filter_field = field(db.StringField(), filterable={"key": "filter_field_name"})
    title = field(
        db.StringField(required=True),
        sortable=True,
        show_as_ref=True,
    )
    slug = field(
        db.SlugField(
            max_length=255, required=True, populate_from="title", update=True, follow=True
        ),
        readonly=True,
    )
    description = field(
        db.StringField(required=True),
        markdown=True,
    )
    url = field(
        db.StringField(required=True),
        description="The remote URL (website)",
        checks=[check_url],
    )
    image_url = db.StringField()
    image = field(
        db.ImageField(
            fs=images,
            basename=default_image_basename,
        ),
        readonly=True,
        show_as_ref=True,
        thumbnail_info={
            "size": BIGGEST_IMAGE_SIZE,
        },
    )
    datasets = field(
        db.ListField(
            field(
                db.ReferenceField("Dataset", reverse_delete_rule=db.PULL),
                nested_fields=dataset_fields,
            ),
        ),
        filterable={
            "key": "dataset",
        },
    )
    tags = field(
        db.TagListField(),
        filterable={
            "key": "tag",
        },
    )

    deleted = field(
        db.DateTimeField(),
    )
    archived = field(
        db.DateTimeField(),
    )

    def __str__(self) -> str:
        return self.title or ""

    @function_field(description="Link to the API endpoint for this fake", show_as_ref=True)
    def uri(self) -> str:
        return "fake/foobar/endpoint/"

    __metrics_keys__: list[str] = [
        "datasets",
        "followers",
        "views",
    ]

    meta: dict = {
        "indexes": [
            "$title",
        ],
        "auto_create_index_on_save": True,
    }


class FakeFactory(ModelFactory):
    class Meta:
        model = Fake

    title = factory.Faker("sentence")
    description = factory.Faker("text")
    url = factory.LazyAttribute(lambda o: "/".join([faker.url(), faker.unique_string()]))
    archived = None


class IndexParserTest:
    index_parser: RequestParser = Fake.__index_parser__
    index_parser_args: list[Argument] = Fake.__index_parser__.args
    index_parser_args_names: set[str] = set([field.name for field in Fake.__index_parser__.args])

    def test_index_parser(self) -> None:
        assert type(self.index_parser) is RequestParser

    def test_filterable_fields_in_parser(self) -> None:
        """All filterable fields should have a parser arg.

        The parser arg uses the `key` provided instead of the field name, so
        - dataset instead of datasets
        - tag instead of tags

        """
        assert set(
            [
                "dataset",
                "tag",
            ]
        ).issubset(self.index_parser_args_names)

    def test_readonly_and_non_wrapped_fields_not_in_parser(self) -> None:
        """Readonly fields() and non wrapped fields should not have a parser arg."""
        for field_ in ["slug", "image_url"]:
            assert field_ not in self.index_parser_args_names

    def test_filterable_fields_from_mixins_in_parser(self) -> None:
        """Filterable fields from mixins should have a parser arg."""
        assert set(["owner", "organization"]).issubset(self.index_parser_args_names)

    def test_additional_filters_in_parser(self) -> None:
        """Filterable fields from the `additional_filters` decorater parameter should have a parser arg."""
        assert "organization_badge" in self.index_parser_args_names

    def test_pagination_fields_in_parser(self) -> None:
        """Pagination fields should have a parser arg."""
        assert "page" in self.index_parser_args_names
        assert "page_size" in self.index_parser_args_names

    def test_searchable(self) -> None:
        """Searchable documents have a `q` parser arg."""
        assert "q" in self.index_parser_args_names

    def test_sortable_fields_in_parser(self) -> None:
        """Sortable fields are listed in the `sort` parser arg choices."""
        sort_arg: Argument = next(arg for arg in self.index_parser_args if arg.name == "sort")
        choices: list[str] = sort_arg.choices
        assert "title" in choices
        assert "-title" in choices

    def test_additional_sorts_in_parser(self) -> None:
        """Additional sorts are listed in the `sort` parser arg choices."""
        sort_arg: Argument = next(arg for arg in self.index_parser_args if arg.name == "sort")
        choices: list[str] = sort_arg.choices
        additional_sorts: list[str] = [
            "datasets",
            "-datasets",
            "followers",
            "-followers",
            "views",
            "-views",
        ]
        assert set(additional_sorts).issubset(set(choices))


class PatchTest:
    class FakeRequest:
        json = {"url": URL_RAISE_ERROR, "description": None}

    def test_patch_check(self) -> None:
        fake: Fake = FakeFactory.create()
        with pytest.raises(ValueError, match=URL_EXISTS_ERROR_MESSAGE):
            patch(fake, self.FakeRequest())

    def test_patch_and_save(self) -> None:
        fake: Fake = FakeFactory.create()
        fake_request = self.FakeRequest()
        fake_request.json["url"] = "ok url"
        with pytest.raises(mongoengine.errors.ValidationError):
            patch_and_save(fake, fake_request)


class ApplySortAndFiltersTest:
    def test_filterable_field(self, app) -> None:
        """A filterable field filters the results."""
        fake1: Fake = FakeFactory(filter_field="test filter")
        fake2: Fake = FakeFactory(filter_field="some other filter")
        with app.test_request_context("/foobar", query_string={"filter_field_name": "test filter"}):
            results: UDataQuerySet = Fake.apply_sort_filters(Fake.objects)
            assert fake1 in results
            assert fake2 not in results

    def test_additional_filters(self, app) -> None:
        """Filtering on an additional filter filters the results."""
        org_public_service: Organization = OrganizationFactory()
        org_public_service.add_badge(org_constants.PUBLIC_SERVICE)
        org_company: Organization = OrganizationFactory()
        org_company.add_badge(org_constants.COMPANY)
        fake1: Fake = FakeFactory(organization=org_public_service)
        fake2: Fake = FakeFactory(organization=org_company)
        with app.test_request_context(
            "/foobar", query_string={"organization_badge": org_constants.PUBLIC_SERVICE}
        ):
            results: UDataQuerySet = Fake.apply_sort_filters(Fake.objects)
            assert fake1 in results
            assert fake2 not in results

    def test_searchable(self, app) -> None:
        """If `@generate_fields(searchable=True)`, then the document can be full-text searched."""
        fake1: Fake = FakeFactory(title="foobar crux")
        fake2: Fake = FakeFactory(title="barbaz crux")
        with app.test_request_context("/foobar", query_string={"q": "foobar"}):
            results: UDataQuerySet = Fake.apply_sort_filters(Fake.objects)
            assert fake1 in results
            assert fake2 not in results

    def test_sortable_field(self, app) -> None:
        """A sortable field should sort the results."""
        fake1: Fake = FakeFactory(title="abc")
        fake2: Fake = FakeFactory(title="def")
        with app.test_request_context("/foobar", query_string={"sort": "title"}):
            results: UDataQuerySet = Fake.apply_sort_filters(Fake.objects)
            assert tuple(results) == (fake1, fake2)
        with app.test_request_context("/foobar", query_string={"sort": "-title"}):
            results = Fake.apply_sort_filters(Fake.objects)
            assert tuple(results) == (fake2, fake1)

    def test_additional_sorts(self, app) -> None:
        """Sorting on additional sort sorts the results."""
        fake1: Fake = FakeFactory(metrics={"datasets": 1})
        fake2: Fake = FakeFactory(metrics={"datasets": 2})
        with app.test_request_context("/foobar", query_string={"sort": "datasets"}):
            results: UDataQuerySet = Fake.apply_sort_filters(Fake.objects)
            assert tuple(results) == (fake1, fake2)
        with app.test_request_context("/foobar", query_string={"sort": "-datasets"}):
            results = Fake.apply_sort_filters(Fake.objects)
            assert tuple(results) == (fake2, fake1)


class ApplyPaginationTest:
    def test_default_pagination(self, app) -> None:
        """Results should be returned with default pagination."""
        [FakeFactory() for _ in range(100)]

        page_arg: Argument = next(arg for arg in Fake.__index_parser__.args if arg.name == "page")
        page_size_arg: Argument = next(
            arg for arg in Fake.__index_parser__.args if arg.name == "page_size"
        )

        with app.test_request_context("/foobar", query_string={}):
            results: DBPaginator = Fake.apply_pagination(Fake.apply_sort_filters(Fake.objects))
            assert results.page_size == page_size_arg.default
            assert results.page == page_arg.default

    def test_paginate(self, app) -> None:
        """Results should be returned paginated."""
        [FakeFactory() for _ in range(100)]

        with app.test_request_context("/foobar", query_string={"page": 3, "page_size": 5}):
            results: DBPaginator = Fake.apply_pagination(Fake.apply_sort_filters(Fake.objects))
            assert results.page_size == 5
            assert results.page == 3
