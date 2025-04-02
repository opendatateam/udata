"""Enhance a MongoEngine document class to give it super powers by decorating it with @generate_fields.

The main goal of `generate_fields` is to remove duplication: we used to have fields declaration in
- models.py
- forms.py
- api_fields.py

Now they're defined in models.py, and adding the `generate_fields` decorator makes them available in the format we need them for the forms or the API.

- default_filterable_field: which field in this document should be the default filter, eg when filtering by Badge, you're actually filtering on `Badge.kind`
- searchable: boolean, if True, the document can be full-text searched using MongoEngine text search
- additional_sorts: add more sorts than the already available ones based on fields (see below). Eg, sort by metrics.
- additional_filters: filter on a field of a field (aka "join"), eg filter on `Reuse__organization__badge=PUBLIC_SERVICE`.


On top of those functionalities added to the document by the `@generate_fields` decorator parameters,
the document fields are parsed and enhanced if they are wrapped in the `field` helper.

- sortable: boolean, if True, it'll be available in the list of sort options
- show_as_ref: add to the list of `ref_fields` (see below)
- readonly: don't add this field to the `write_fields`
- markdown: use Mardown to format this field instead of plain old text
- filterable: this field can be filtered on. It's either an empty dictionnary, either {`key`: `field_name`} if the `field_name` to use is different from the original field, eg `dataset` instead of `datasets`.
- description: use as the info on the field in the swagger forms.
- check: provide a function to validate the content of the field.
- thumbnail_info: add additional info for a thumbnail, eg `{ "size": BIGGEST_IMAGE_SIZE }`.

You may also use the `@function_field` decorator to treat a document method as a field.


The following fields are added on the document class once decorated:

- ref_fields: list of fields to return when embedding/referencing a document, eg when querying Reuse.organization, only return a subset of the org fields
- read_fields: all of the fields to return when querying a document
- write_fields: list of fields to provide when creating a document, eg when creating a Reuse, we only provide organization IDs, not all the org fields

"""

import functools
from typing import Any, Callable, Iterable

import flask_restx.fields as restx_fields
import mongoengine
import mongoengine.fields as mongo_fields
from bson import DBRef, ObjectId
from flask_restx.inputs import boolean
from flask_restx.reqparse import RequestParser
from flask_storage.mongo import ImageField as FlaskStorageImageField

import udata.api.fields as custom_restx_fields
from udata.api import api, base_reference
from udata.mongo.errors import FieldValidationError
from udata.mongo.queryset import DBPaginator, UDataQuerySet

lazy_reference = api.model(
    "LazyReference",
    {
        "class": restx_fields.Raw(attribute=lambda ref: ref.document_type.__name__),
        "id": restx_fields.Raw(attribute=lambda ref: ref.pk),
    },
)


def convert_db_to_field(key, field, info) -> tuple[Callable | None, Callable | None]:
    """Map a Mongo field to a Flask RestX field.

    Most of the types are a simple 1-to-1 mapping except lists and references that requires
    more work.
    We currently only map the params that we use from Mongo to RestX (for example min_length / max_length…).

    In the first part of the function we save the RestX constructor as a lambda because we need to call it with the
    params. Since merging the params involve a litte bit of work (merging default params with read/write params and then with
    user-supplied overrides, setting the readonly flag…), it's easier to have to do this only once at the end of the function.

    """
    params: dict = {}
    params["required"] = field.required

    read_params: dict = {}
    write_params: dict = {}

    constructor: Callable
    constructor_read: Callable | None = None
    constructor_write: Callable | None = None

    if info.get("convert_to"):
        # TODO: this is currently never used. We may remove it if the auto-conversion
        # is always good enough.
        return info.get("convert_to"), info.get("convert_to")
    elif isinstance(field, mongo_fields.StringField):
        constructor = (
            custom_restx_fields.Markdown if info.get("markdown", False) else restx_fields.String
        )
        params["min_length"] = field.min_length
        params["max_length"] = field.max_length
        params["enum"] = field.choices
        if field.validation:
            params["validation"] = validation_to_type(field.validation)
    elif isinstance(field, mongo_fields.ObjectIdField):
        constructor = restx_fields.String
    elif isinstance(field, mongo_fields.FloatField):
        constructor = restx_fields.Float
        params["min"] = field.min  # TODO min_value?
        params["max"] = field.max
    elif isinstance(field, mongo_fields.BooleanField):
        constructor = restx_fields.Boolean
    elif isinstance(field, mongo_fields.DateTimeField):
        constructor = custom_restx_fields.ISODateTime
    elif isinstance(field, mongo_fields.DictField):
        constructor = restx_fields.Raw
    elif isinstance(field, mongo_fields.ImageField) or isinstance(field, FlaskStorageImageField):
        size: int | None = info.get("size", None)
        if size:
            params["description"] = f"URL of the cropped and squared image ({size}x{size})"
        else:
            params["description"] = "URL of the image"

        if info.get("is_thumbnail", False):
            constructor_read = custom_restx_fields.ImageField
            write_params["read_only"] = True
        else:
            constructor = custom_restx_fields.ImageField

    elif isinstance(field, mongo_fields.ListField):
        # For lists, we can expose them only by showing a link to the API
        # with the results of the list to avoid listing a lot of sub-ressources
        # (for example for a dataservices with thousands of datasets).
        href = info.get("href", None)
        if href:

            def constructor_read(**kwargs):
                return restx_fields.Raw(
                    attribute=lambda o: {
                        "rel": "subsection",
                        "href": href(o),
                        "type": "GET",
                        "total": len(o[key]),
                    },
                    description="Visit this API link to see the list.",
                    **kwargs,
                )

        # If it's a standard list, we convert the inner value from Mongo to RestX then we create
        # the `List` RestX type with this converted inner value.
        # There is three level of information, from most important to least
        #     1. `inner_field_info` inside `__additional_field_info__` on the parent
        #     2. `__additional_field_info__` of the inner field
        #     3. `__additional_field_info__` of the parent
        inner_info: dict = getattr(field.field, "__additional_field_info__", {})
        field_read, field_write = convert_db_to_field(
            f"{key}.inner", field.field, {**info, **inner_info, **info.get("inner_field_info", {})}
        )

        if constructor_read is None:
            # We don't want to set the `constructor_read` if it's already set
            # by the `href` code above.
            def constructor_read(**kwargs):
                return restx_fields.List(field_read, **kwargs)

        # But we want to keep the `constructor_write` to allow changing the list.
        def constructor_write(**kwargs):
            return restx_fields.List(field_write, **kwargs)

    elif isinstance(
        field, (mongo_fields.GenericReferenceField, mongoengine.fields.GenericLazyReferenceField)
    ):

        def constructor(**kwargs):
            return restx_fields.Nested(lazy_reference, **kwargs)

    elif isinstance(field, mongo_fields.ReferenceField | mongo_fields.LazyReferenceField):
        # For reference we accept while writing a String representing the ID of the referenced model.
        # For reading, if the user supplied a `nested_fields` (RestX model), we use it to convert
        # the referenced model, if not we return a String (and RestX will call the `str()` of the model
        # when returning from an endpoint)
        nested_fields: dict | None = info.get("nested_fields")
        if nested_fields is None:
            # If there is no `nested_fields` convert the object to the string representation.
            constructor_read = restx_fields.String
        else:

            def constructor_read(**kwargs):
                return restx_fields.Nested(nested_fields, **kwargs)

        write_params["description"] = "ID of the reference"
        constructor_write = restx_fields.String
    elif isinstance(field, mongo_fields.EmbeddedDocumentField):
        nested_fields = info.get("nested_fields")
        if nested_fields is not None:

            def constructor(**kwargs):
                return restx_fields.Nested(nested_fields, **kwargs)

        elif hasattr(field.document_type_obj, "__read_fields__"):

            def constructor_read(**kwargs):
                return restx_fields.Nested(field.document_type_obj.__read_fields__, **kwargs)

            def constructor_write(**kwargs):
                return restx_fields.Nested(field.document_type_obj.__write_fields__, **kwargs)

        else:
            raise ValueError(
                f"EmbeddedDocumentField `{key}` requires a `nested_fields` param to serialize/deserialize or a `@generate_fields()` definition."
            )

    else:
        raise ValueError(f"Unsupported MongoEngine field type {field.__class__}")

    read_params = {**params, **read_params, **info}
    write_params = {**params, **write_params, **info}

    read: Callable = (
        constructor_read(**read_params) if constructor_read else constructor(**read_params)
    )
    if write_params.get("readonly", False) or (constructor_write is None and constructor is None):
        write: Callable | None = None
    else:
        write = (
            constructor_write(**write_params) if constructor_write else constructor(**write_params)
        )
    return read, write


def get_fields(cls) -> Iterable[tuple[str, Callable, dict]]:
    """Return all the document fields that are wrapped with the `field()` helper.

    Also expand image fields to add thumbnail fields.

    """
    for key, field in cls._fields.items():
        info: dict | None = getattr(field, "__additional_field_info__", None)
        if info is None:
            continue

        yield key, field, info

        if isinstance(field, mongo_fields.ImageField) or isinstance(field, FlaskStorageImageField):
            yield (
                f"{key}_thumbnail",
                field,
                {**info, **info.get("thumbnail_info", {}), "is_thumbnail": True, "attribute": key},
            )


def generate_fields(**kwargs) -> Callable:
    """Mongoengine document decorator.

    This decorator will create two auto-generated attributes on the class `__read_fields__` and `__write_fields__`
    that can be used in API endpoint inside `expect()` and `marshall_with()`.

    It will also
    - generate an API parameter parser
    - sort and filter a list of documents with the provided params using the `apply_sort_filters` helper
    - apply a pagination with page and page size args with the `apply_pagination` helper

    """

    def wrapper(cls) -> Callable:
        from udata.models import db

        read_fields: dict = {}
        write_fields: dict = {}
        ref_fields: dict = {}
        sortables: list = kwargs.get("additional_sorts", [])

        filterables: list[dict] = []
        additional_filters: dict[str, dict] = get_fields_with_additional_filters(
            kwargs.get("additional_filters", {})
        )

        read_fields["id"] = restx_fields.String(required=True, readonly=True)

        for key, field, info in get_fields(cls):
            sortable_key: bool = info.get("sortable", False)
            if sortable_key:
                sortables.append(
                    {
                        "key": sortable_key if isinstance(sortable_key, str) else key,
                        "value": key,
                    }
                )

            filterable: dict[str, Any] | None = info.get("filterable", None)
            if filterable is not None:
                filterables.append(compute_filter(key, field, info, filterable))

            additional_filter: dict | None = additional_filters.get(key, None)
            if additional_filter:
                if not isinstance(
                    field, mongo_fields.ReferenceField | mongo_fields.LazyReferenceField
                ):
                    raise Exception("Cannot use additional_filters on a field that is not a ref.")

                ref_model: db.Document = field.document_type

                for child in additional_filter.get("children", []):
                    inner_field: str = getattr(ref_model, child["key"])

                    column: str = f"{key}__{child['key']}"
                    child["key"] = f"{key}_{child['key']}"
                    filterable = compute_filter(column, inner_field, info, child)

                    # Since MongoDB is not capable of doing joins with a column like `organization__slug` we need to
                    # do a custom filter by splitting the query in two.

                    def query(filterable, query, value) -> UDataQuerySet:
                        # We use the computed `filterable["column"]` here because the `compute_filter` function
                        # could have added a default filter at the end (for example `organization__badges` converted
                        # in `organization__badges__kind`)
                        parts = filterable["column"].split("__", 1)
                        models: UDataQuerySet = ref_model.objects.filter(**{parts[1]: value}).only(
                            "id"
                        )
                        return query.filter(**{f"{parts[0]}__in": models})

                    # do a query-based filter instead of a column based one
                    filterable["query"] = functools.partial(query, filterable)
                    filterables.append(filterable)

            read, write = convert_db_to_field(key, field, info)

            if read:
                read_fields[key] = read
            if write:
                write_fields[key] = write

            if read and info.get("show_as_ref", False):
                ref_fields[key] = read

        # The goal of this loop is to fetch all functions (getters) of the class
        # If a function has an `__additional_field_info__` attribute it means
        # it has been decorated with `@function_field()` and should be included
        # in the API response.
        for method_name in dir(cls):
            if method_name == "objects":
                continue
            if method_name.startswith("_"):
                continue
            if method_name in read_fields:
                continue  # Do not override if the attribute is also callable like for Extras

            method = getattr(cls, method_name)
            if not callable(method):
                continue

            additional_field_info = getattr(method, "__additional_field_info__", None)
            if additional_field_info is None:
                continue

            def make_lambda(method):
                """
                Factory function to create a lambda with the correct scope.
                If we don't have this factory function, the `method` will be the
                last method assigned in this loop?
                """
                return lambda o: method(o)

            read_fields[method_name] = restx_fields.String(
                attribute=make_lambda(method), **{"readonly": True, **additional_field_info}
            )
            if additional_field_info.get("show_as_ref", False):
                ref_fields[method_name] = read_fields[method_name]

        cls.__read_fields__ = api.model(f"{cls.__name__} (read)", read_fields, **kwargs)
        cls.__write_fields__ = api.model(f"{cls.__name__} (write)", write_fields, **kwargs)
        cls.__ref_fields__ = api.inherit(f"{cls.__name__}Reference", base_reference, ref_fields)

        mask: str | None = kwargs.pop("mask", None)
        if mask is not None:
            mask = "data{{{0}}},*".format(mask)
        cls.__page_fields__ = api.model(
            f"{cls.__name__}Page",
            custom_restx_fields.pager(cls.__read_fields__),
            mask=mask,
            **kwargs,
        )

        # Parser for index sort/filters
        paginable: bool = kwargs.get("paginable", True)
        parser: RequestParser = api.parser()

        if paginable:
            parser.add_argument(
                "page", type=int, location="args", default=1, help="The page to display"
            )
            parser.add_argument(
                "page_size", type=int, location="args", default=20, help="The page size"
            )

        if sortables:
            choices: list[str] = [sortable["key"] for sortable in sortables] + [
                "-" + sortable["key"] for sortable in sortables
            ]
            parser.add_argument(
                "sort",
                type=str,
                location="args",
                choices=choices,
                help="The field (and direction) on which sorting apply",
            )

        searchable: bool = kwargs.pop("searchable", False)
        if searchable:
            parser.add_argument("q", type=str, location="args")

        for filterable in filterables:
            parser.add_argument(
                # Use the custom label from `additional_filters` if there's one.
                filterable.get("label", filterable["key"]),
                type=filterable["type"],
                location="args",
                choices=filterable.get("choices", None),
            )

        cls.__index_parser__ = parser

        def apply_sort_filters(base_query) -> UDataQuerySet:
            args = cls.__index_parser__.parse_args()

            if sortables and args["sort"]:
                negate: bool = args["sort"].startswith("-")
                sort_key: str = args["sort"][1:] if negate else args["sort"]

                sort_by: str | None = next(
                    (sortable["value"] for sortable in sortables if sortable["key"] == sort_key),
                    None,
                )
                if sort_by:
                    if negate:
                        sort_by = "-" + sort_by

                    base_query = base_query.order_by(sort_by)

            if searchable and args.get("q"):
                phrase_query: str = " ".join([f'"{elem}"' for elem in args["q"].split(" ")])
                base_query = base_query.search_text(phrase_query)

            for filterable in filterables:
                # If it's from an `additional_filter`, use the custom label instead of the key,
                # eg use `organization_badge` instead of `organization.badges` which is
                # computed to `organization_badges`.
                filter = args.get(filterable.get("label", filterable["key"]))
                if filter is not None:
                    for constraint in filterable.get("constraints", []):
                        if constraint == "objectid" and not ObjectId.is_valid(
                            args[filterable["key"]]
                        ):
                            api.abort(400, f"`{filterable['key']}` must be an identifier")

                    query = filterable.get("query", None)
                    if query:
                        base_query = filterable["query"](base_query, filter)
                    else:
                        base_query = base_query.filter(
                            **{
                                filterable["column"]: filter,
                            }
                        )

            return base_query

        def apply_pagination(base_query) -> DBPaginator:
            args = cls.__index_parser__.parse_args()

            if paginable:
                base_query = base_query.paginate(args["page"], args["page_size"])
            return base_query

        cls.apply_sort_filters = apply_sort_filters
        cls.apply_pagination = apply_pagination
        cls.__additional_class_info__ = kwargs
        return cls

    return wrapper


def function_field(**info) -> Callable:
    def inner(func):
        func.__additional_field_info__ = info
        return func

    return inner


def field(inner, **kwargs):
    """Simple wrapper to make a document field visible for the API.

    We can pass additional arguments that will be forwarded to the RestX field constructor.

    """
    inner.__additional_field_info__ = kwargs
    return inner


def patch(obj, request) -> type:
    """Patch the object with the data from the request.

    Only fields decorated with the `field()` decorator will be read (and not readonly).

    """
    from udata.mongo.engine import db

    for key, value in request.json.items():
        field = obj.__write_fields__.get(key)
        if field is not None and not field.readonly:
            model_attribute = getattr(obj.__class__, key)

            if hasattr(model_attribute, "from_input"):
                value = model_attribute.from_input(value)
            elif isinstance(model_attribute, mongoengine.fields.ListField) and isinstance(
                model_attribute.field,
                mongo_fields.ReferenceField | mongo_fields.LazyReferenceField,
            ):
                # TODO `wrap_primary_key` do Mongo request, do a first pass to fetch all documents before calling it (to avoid multiple queries).
                value = [wrap_primary_key(key, model_attribute.field, id) for id in value]
            elif isinstance(
                model_attribute, mongo_fields.ReferenceField | mongo_fields.LazyReferenceField
            ):
                value = wrap_primary_key(key, model_attribute, value)
            elif isinstance(
                model_attribute,
                (
                    mongoengine.fields.GenericReferenceField,
                    mongoengine.fields.GenericLazyReferenceField,
                ),
            ):
                value = wrap_primary_key(
                    key,
                    model_attribute,
                    value["id"],
                    document_type=db.resolve_model(value["class"]),
                )

            info = getattr(model_attribute, "__additional_field_info__", {})

            # `checks` field attribute allows to do validation from the request before setting
            # the attribute
            checks = info.get("checks", [])

            if is_value_modified(getattr(obj, key), value):
                for check in checks:
                    check(
                        value,
                        **{
                            "is_creation": obj._created,
                            "is_update": not obj._created,
                            "field": key,
                        },
                    )  # TODO add other model attributes in function parameters

            setattr(obj, key, value)

    return obj


def is_value_modified(old_value, new_value) -> bool:
    # If we want to modify a reference, the new_value may be a DBRef.
    # `wrap_primary_key` can also return the `foreign_document` (see :WrapToForeignDocument)
    # and it is not currently taken into account here…
    # Maybe we can do another type of check to check if the reference changes in the future…
    if isinstance(new_value, DBRef):
        return not old_value or new_value.id != old_value.id

    return new_value != old_value


def patch_and_save(obj, request) -> type:
    obj = patch(obj, request)
    obj.save()

    return obj


def wrap_primary_key(
    field_name: str,
    foreign_field: mongoengine.fields.ReferenceField | mongoengine.fields.GenericReferenceField,
    value: str | None,
    document_type=None,
):
    """Wrap the `String` inside an `ObjectId`.

    If the foreign ID is a `String`, get a `DBRef` from the database.

    TODO: we only check the document reference if the ID is a `String` field (not in the case of a classic `ObjectId`).

    """
    if value is None:
        return value

    if isinstance(value, dict) and "id" in value:
        return wrap_primary_key(field_name, foreign_field, value["id"], document_type)

    document_type = document_type or foreign_field.document_type().__class__
    id_field_name = document_type._meta["id_field"]

    id_field = getattr(document_type, id_field_name)

    # Get the foreign document from MongoDB because the othewise it fails during read
    # Also useful to get a DBRef for non ObjectId references (see below)
    foreign_document = document_type.objects(**{id_field_name: value}).first()
    if foreign_document is None:
        raise FieldValidationError(field=field_name, message=f"Unknown reference '{value}'")

    # GenericReferenceField only accepts document (not dbref / objectid)
    # :WrapToForeignDocument
    if isinstance(
        foreign_field,
        (
            mongoengine.fields.GenericReferenceField,
            mongoengine.fields.GenericLazyReferenceField,
        ),
    ):
        return foreign_document

    if isinstance(id_field, mongoengine.fields.ObjectIdField):
        return foreign_document.to_dbref()
    elif isinstance(id_field, mongoengine.fields.StringField):
        # Right now I didn't find a simpler way to make mongoengine happy.
        # For references, it expects `ObjectId`, `DBRef`, `LazyReference` or `document` but since
        # the primary key a StringField (not an `ObjectId`) we cannot create an `ObjectId`, I didn't find
        # a way to create a `DBRef` nor a `LazyReference` so I create a simple document with only the ID field.
        # We could use a simple dict as follow instead:
        # { 'id': value }
        # … but it may be important to check before-hand that the reference point to a correct document.
        return foreign_document.to_dbref()
    else:
        raise ValueError(
            f"Unknown ID field type {id_field.__class__} for {document_type} (ID field name is {id_field_name}, value was {value})"
        )


def get_fields_with_additional_filters(additional_filters: dict[str, str]) -> dict[str, Any]:
    """Filter on additional related fields.

    Right now we only support additional filters with a depth of two, eg "organization.badges".

    The goal of this function is to key by the additional filters by the first part (`organization`) to
    be able to compute them when we loop over all the fields (`title`, `organization`…)


    The `additional_filters` property is a dict: {"label": "key"}, for example {"organization_badge": "organization.badges"}.
    The `label` will be the name of the parser arg, like `?organization_badge=public-service`, which makes more
    sense than `?organization_badges=public-service`.
    """
    results: dict = {}
    for label, key in additional_filters.items():
        parts = key.split(".")
        if len(parts) == 2:
            parent = parts[0]
            child = parts[1]

            if parent not in results:
                results[parent] = {"children": []}

            results[parent]["children"].append(
                {
                    # The name for the parser argument, so `organization_badge` instead of `organization_badges`.
                    "label": label,
                    "key": child,
                    "type": str,
                }
            )
        else:
            raise Exception(f"Do not support `additional_filters` without two parts: {key}.")

    return results


def compute_filter(column: str, field, info, filterable) -> dict:
    # "key" is the param key in the URL
    if "key" not in filterable:
        filterable["key"] = column

    # If we do a filter on a embed document, get the class info
    # of this document to see if there is a default filter value
    embed_info = None
    if isinstance(field, mongo_fields.EmbeddedDocumentField):
        embed_info = field.get("__additional_class_info__", None)
    elif isinstance(field, mongo_fields.EmbeddedDocumentListField):
        embed_info = getattr(field.field.document_type, "__additional_class_info__", None)

    if embed_info and embed_info.get("default_filterable_field", None):
        # There is a default filterable field so append it to the column and replace the
        # field to use the inner one (for example using the `kind` `StringField` instead of
        # the embed `Badge` field.)
        filterable["column"] = f"{column}__{embed_info['default_filterable_field']}"
        field = getattr(field.field.document_type, embed_info["default_filterable_field"])
    else:
        filterable["column"] = column

    if "constraints" not in filterable:
        filterable["constraints"] = []

    if isinstance(field, mongo_fields.ReferenceField | mongo_fields.LazyReferenceField) or (
        isinstance(field, mongo_fields.ListField)
        and isinstance(field.field, mongo_fields.ReferenceField | mongo_fields.LazyReferenceField)
    ):
        filterable["constraints"].append("objectid")

    if "type" not in filterable:
        if isinstance(field, mongo_fields.BooleanField):
            filterable["type"] = boolean
        else:
            filterable["type"] = str
    if field.validation:
        filterable["type"] = validation_to_type(field.validation)

    filterable["choices"] = info.get("choices", None)
    if hasattr(field, "choices") and field.choices:
        filterable["choices"] = field.choices

    return filterable


def validation_to_type(validation: Callable) -> Callable:
    """Convert a mongo field's validation function to a ReqParser's type.

    In flask_restx.ReqParser, validation is done by setting the param's type to
    a callable that will either raise, or return the parsed value.

    In mongo, a field's validation function cannot return anything, so this
    helper wraps the mongo field's validation to return the value if it validated.
    """
    from udata.models import db

    def wrapper(value: str) -> str:
        try:
            validation(value)
        except db.ValidationError:
            raise
        return value

    wrapper.__schema__ = {"type": "string", "format": "my-custom-format"}

    return wrapper
