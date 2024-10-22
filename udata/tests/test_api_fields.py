import factory
import pytest
from flask_restx.reqparse import RequestParser
from werkzeug.exceptions import BadRequest

from udata.api_fields import field, function_field, generate_fields, patch, patch_and_save
from udata.core.dataset.api_fields import dataset_fields
from udata.core.organization import constants as org_constants
from udata.core.organization.factories import OrganizationFactory
from udata.core.owned import Owned
from udata.core.storages import default_image_basename, images
from udata.factories import ModelFactory
from udata.models import Badge, BadgeMixin, BadgesList, WithMetrics, db
from udata.utils import faker

pytestmark = [
    pytest.mark.usefixtures("clean_db"),
]

BIGGEST_IMAGE_SIZE = 500

BADGES = {
    "badge-1": "badge 1",
    "badge-2": "badge 2",
}

URL_RAISE_ERROR = "/raise/validation/error"
URL_EXISTS_ERROR_MESSAGE = "Url exists"


def check_url(url=""):
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
    additional_filters=[
        "organization.badges",
    ],
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
        check=check_url,
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

    def __str__(self):
        return self.title or ""

    @function_field(description="Link to the API endpoint for this fake", show_as_ref=True)
    def uri(self):
        return "fake/foobar/endpoint/"

    __metrics_keys__ = [
        "datasets",
        "followers",
        "views",
    ]

    meta = {
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
    index_parser = Fake.__index_parser__
    index_parser_args = Fake.__index_parser__.args
    index_parser_args_names = set([field.name for field in Fake.__index_parser__.args])

    def test_index_parser(self):
        assert type(self.index_parser) is RequestParser

    def test_filterable_fields_in_parser(self):
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

    def test_readonly_and_non_wrapped_fields_not_in_parser(self):
        """Readonly fields() and non wrapped fields should not have a parser arg."""
        for field_ in ["slug", "image_url"]:
            assert field_ not in self.index_parser_args_names

    def test_filterable_fields_from_mixins_in_parser(self):
        """Filterable fields from mixins should have a parser arg."""
        assert set(["owner", "organization"]).issubset(self.index_parser_args_names)

    def test_additional_filters_in_parser(self):
        """Filterable fields from the `additional_filters` decorater parameter should have a parser arg."""
        assert "organization_badges" in self.index_parser_args_names

    def test_pagination_fields_in_parser(self):
        """Pagination fields should have a parser arg."""
        assert "page" in self.index_parser_args_names
        assert "page_size" in self.index_parser_args_names

    def test_searchable(self):
        """Searchable documents have a `q` parser arg."""
        assert "q" in self.index_parser_args_names

    def test_sortable_fields_in_parser(self):
        """Sortable fields are listed in the `sort` parser arg choices."""
        sort_arg = next(arg for arg in self.index_parser_args if arg.name == "sort")
        choices = sort_arg.choices
        assert "title" in choices
        assert "-title" in choices

    def test_additional_sorts_in_parser(self):
        """Additional sorts are listed in the `sort` parser arg choices."""
        sort_arg = next(arg for arg in self.index_parser_args if arg.name == "sort")
        choices = sort_arg.choices
        additional_sorts = ["datasets", "-datasets", "followers", "-followers", "views", "-views"]
        assert set(additional_sorts).issubset(set(choices))


class PatchTest:
    class FakeRequest:
        json = {"url": URL_RAISE_ERROR, "description": None}

    def test_patch_check(self):
        fake = FakeFactory.create()
        with pytest.raises(ValueError, match=URL_EXISTS_ERROR_MESSAGE):
            patch(fake, self.FakeRequest())

    def test_patch_and_save(self):
        fake = FakeFactory.create()
        fake_request = self.FakeRequest()
        fake_request.json["url"] = "ok url"
        with pytest.raises(BadRequest):
            patch_and_save(fake, fake_request)


class ApplySortAndFiltersTest:
    def test_filterable_field(self, app):
        """A filterable field filters the results."""
        fake1 = FakeFactory(filter_field="test filter")
        fake2 = FakeFactory(filter_field="some other filter")
        with app.test_request_context("/foobar", query_string={"filter_field_name": "test filter"}):
            results = Fake.apply_sort_filters_and_pagination(Fake.objects)
            assert fake1 in results
            assert fake2 not in results

    def test_additional_filters(self, app):
        """Filtering on an additional filter filters the results."""
        org_public_service = OrganizationFactory()
        org_public_service.add_badge(org_constants.PUBLIC_SERVICE)
        org_company = OrganizationFactory()
        org_company.add_badge(org_constants.COMPANY)
        fake1 = FakeFactory(organization=org_public_service)
        fake2 = FakeFactory(organization=org_company)
        with app.test_request_context(
            "/foobar", query_string={"organization_badges": org_constants.PUBLIC_SERVICE}
        ):
            results = Fake.apply_sort_filters_and_pagination(Fake.objects)
            assert fake1 in results
            assert fake2 not in results

    def test_searchable(self, app):
        """If `@generate_fields(searchable=True)`, then the document can be full-text searched."""
        fake1 = FakeFactory(title="foobar crux")
        fake2 = FakeFactory(title="barbaz crux")
        with app.test_request_context("/foobar", query_string={"q": "foobar"}):
            results = Fake.apply_sort_filters_and_pagination(Fake.objects)
            assert fake1 in results
            assert fake2 not in results

    def test_sortable_field(self, app):
        """A sortable field should sort the results."""
        fake1 = FakeFactory(title="abc")
        fake2 = FakeFactory(title="def")
        with app.test_request_context("/foobar", query_string={"sort": "title"}):
            results = Fake.apply_sort_filters_and_pagination(Fake.objects)
            assert tuple(results) == (fake1, fake2)
        with app.test_request_context("/foobar", query_string={"sort": "-title"}):
            results = Fake.apply_sort_filters_and_pagination(Fake.objects)
            assert tuple(results) == (fake2, fake1)

    def test_additional_sorts(self, app):
        """Sorting on additional sort sorts the results."""
        fake1 = FakeFactory(metrics={"datasets": 1})
        fake2 = FakeFactory(metrics={"datasets": 2})
        with app.test_request_context("/foobar", query_string={"sort": "datasets"}):
            results = Fake.apply_sort_filters_and_pagination(Fake.objects)
            assert tuple(results) == (fake1, fake2)
        with app.test_request_context("/foobar", query_string={"sort": "-datasets"}):
            results = Fake.apply_sort_filters_and_pagination(Fake.objects)
            assert tuple(results) == (fake2, fake1)
