from flask_restx.reqparse import RequestParser

from udata.api_fields import field, function_field, generate_fields
from udata.core.dataset.api_fields import dataset_fields
from udata.core.owned import Owned
from udata.core.storages import default_image_basename, images
from udata.models import Badge, BadgeMixin, BadgesList, WithMetrics, db
from udata.mongo.errors import FieldValidationError

BIGGEST_IMAGE_SIZE = 500

BADGES = {
    "badge-1": "badge 1",
    "badge-2": "badge 2",
}


def check_url_does_not_exists(url):
    """Ensure a URL is not yet registered"""
    if url and Fake.url_exists(url):
        raise FieldValidationError("This URL is already registered", field="url")


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
        check=check_url_does_not_exists,
    )
    urlhash = db.StringField(required=True, unique=True)
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
        "discussions",
        "datasets",
        "followers",
        "views",
    ]


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
        for field_ in ["slug", "urlhash", "image_url"]:
            assert field_ not in self.index_parser_args_names

    def test_filterable_fields_from_mixins_in_parser(self):
        """Filterable fields from mixins should have a parser arg."""
        assert set(["owner", "organization", "organization_badges"]).issubset(
            self.index_parser_args_names
        )

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
