from flask import current_app, has_request_context, request
from flask_restx.mask import Mask
from mongoengine import EmbeddedDocument
from mongoengine.base.datastructures import BaseList
from mongoengine.errors import ValidationError
from mongoengine.fields import EmbeddedDocumentListField, ListField, ReferenceField, StringField

from udata.api import api
from udata.api_fields import field, generate_fields
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.api_fields import dataset_fields
from udata.core.reuse.models import Reuse
from udata.mongo.uuid_fields import AutoUUIDField


@generate_fields()
class Bloc(EmbeddedDocument):
    meta = {"allow_inheritance": True}

    id = field(AutoUUIDField(primary_key=True))


class BlocWithTitleMixin:
    title = field(StringField(required=True))
    subtitle = field(StringField())


DATASET_CARD_MASK = "{id,title,acronym,slug,description,page,uri,private,archived,organization,owner,last_update,quality,metrics,badges,tags}"
dataset_card_fields = api.model("Dataset (card)", dict(dataset_fields), mask=DATASET_CARD_MASK)

REUSE_CARD_MASK = "{id,title,slug,description,type,url,image,image_thumbnail,page,uri,organization,owner,metrics,badges,tags,topic,private,created_at,last_modified}"
reuse_card_fields = api.model("Reuse (card)", dict(Reuse.__read_fields__), mask=REUSE_CARD_MASK)

DATASERVICE_CARD_MASK = "{id,title,acronym,slug,description,base_api_url,format,self_api_url,self_web_url,organization,owner,metrics,badges,tags,private,created_at,metadata_modified_at}"
dataservice_card_fields = api.model(
    "Dataservice (card)", dict(Dataservice.__read_fields__), mask=DATASERVICE_CARD_MASK
)


@generate_fields()
class DatasetsListBloc(BlocWithTitleMixin, Bloc):
    datasets = field(
        ListField(
            field(
                ReferenceField("Dataset"),
                nested_fields=dataset_card_fields,
            )
        )
    )


@generate_fields()
class ReusesListBloc(BlocWithTitleMixin, Bloc):
    reuses = field(
        ListField(
            field(
                ReferenceField("Reuse"),
                nested_fields=reuse_card_fields,
            )
        )
    )


@generate_fields()
class DataservicesListBloc(BlocWithTitleMixin, Bloc):
    dataservices = field(
        ListField(
            field(
                ReferenceField("Dataservice"),
                nested_fields=dataservice_card_fields,
            )
        )
    )


@generate_fields()
class LinkInBloc(EmbeddedDocument):
    title = field(StringField(required=True))
    color = field(StringField())
    url = field(StringField())


@generate_fields()
class LinksListBloc(BlocWithTitleMixin, Bloc):
    paragraph = field(StringField())
    main_link_url = field(StringField())
    main_link_title = field(StringField())

    links = field(EmbeddedDocumentListField(LinkInBloc))


HERO_COLORS = ("primary", "green", "purple")


@generate_fields()
class HeroBloc(Bloc):
    title = field(StringField(required=True))
    description = field(StringField())
    color = field(StringField(choices=HERO_COLORS))
    main_link_url = field(StringField())
    main_link_title = field(StringField())


@generate_fields()
class MarkdownBloc(Bloc):
    # Not using BlocWithTitleMixin because title should be optional here
    title = field(StringField())
    subtitle = field(StringField())
    content = field(
        StringField(required=True),
        markdown=True,
    )


BLOCS_DISALLOWED_IN_ACCORDION = ("AccordionListBloc", "HeroBloc")


def check_no_recursive_blocs(blocs, **kwargs):
    for bloc in blocs:
        if bloc.__class__.__name__ in BLOCS_DISALLOWED_IN_ACCORDION:
            raise ValidationError(f"{bloc.__class__.__name__} cannot be nested inside an accordion")


@generate_fields()
class AccordionItemBloc(EmbeddedDocument):
    title = field(StringField(required=True))
    content = field(
        EmbeddedDocumentListField(Bloc),
        generic=True,
        checks=[check_no_recursive_blocs],
    )


@generate_fields()
class AccordionListBloc(Bloc):
    title = field(StringField())
    description = field(StringField())
    items = field(EmbeddedDocumentListField(AccordionItemBloc))


SITE_BLOCS_FIELDS = ("datasets_blocs", "reuses_blocs", "dataservices_blocs")


def _is_field_in_response_mask(read_fields, field_name) -> bool:
    """Tell whether a top-level field will be serialized given the request mask.

    The effective mask is the `X-Fields` request header if present, else the model's
    default mask. A field is kept when it is listed in the mask, or when the mask
    contains the `*` wildcard. No mask means every field is serialized.
    """
    mask_str = getattr(read_fields, "__mask__", None)
    if has_request_context():
        header = current_app.config["RESTX_MASK_HEADER"]
        mask_str = request.headers.get(header) or mask_str
    if not mask_str:
        return True
    mask = Mask(mask_str)
    return field_name in mask or "*" in mask


def prefetch_blocs_references(document_cls, obj, *bloc_fields):
    """Batch-load the datasets/reuses/dataservices referenced by an object's blocs.

    Marshalling blocs serializes each referenced object as a card including its
    `organization` (and `owner`). MongoEngine dereferences each reference — and each
    reference's own organization/owner — one query at a time, with no cross-instance
    cache. A page with dozens of cards therefore triggers hundreds of sequential
    queries (one per organization), which dominates the response time.

    We collect every reference across the whole (possibly accordion-nested) bloc tree,
    reload each type as a single flat query with `select_related` (which batches the
    organization/owner lookups), and inject the resolved documents back into the blocs.
    Marshalling then issues no further query.

    `document_cls` is the marshalled document class (Post, Site, …), `obj` its instance
    and `bloc_fields` the names of its bloc list attributes (e.g. `"blocs"`, or the
    Site's three bloc fields). Bloc fields excluded by the response mask are skipped, so
    masked-out blocs (e.g. on the default `/site/` response) add no latency.
    """
    included = [
        name
        for name in bloc_fields
        if _is_field_in_response_mask(document_cls.__read_fields__, name)
    ]
    if not included:
        return

    # (bloc, attr, model, [referenced ids]) for every bloc holding references.
    collected: list[tuple] = []

    def walk(blocs):
        for bloc in blocs:
            for attr, mongo_field in type(bloc)._fields.items():
                if isinstance(mongo_field, ListField) and isinstance(
                    mongo_field.field, ReferenceField
                ):
                    # A `ListField(ReferenceField)`: read the raw references from `_data`
                    # to avoid a per-bloc dereference (we batch them across all blocs).
                    refs = bloc._data.get(attr) or []
                    model = mongo_field.field.document_type
                    collected.append((bloc, attr, model, [ref.id for ref in refs]))
                elif isinstance(mongo_field, EmbeddedDocumentListField):
                    # Recurse into nested blocs (e.g. accordion items -> content).
                    walk(getattr(bloc, attr) or [])

    for name in included:
        walk(getattr(obj, name))

    ids_by_model: dict = {}
    for _, _, model, ids in collected:
        ids_by_model.setdefault(model, set()).update(ids)

    docs_by_model = {
        model: {doc.id: doc for doc in model.objects(id__in=list(ids)).select_related()}
        for model, ids in ids_by_model.items()
    }

    for bloc, attr, model, ids in collected:
        by_id = docs_by_model[model]
        # Mark the list as already dereferenced so marshalling reads it as-is instead
        # of dereferencing each reference (and its organization) again.
        resolved = BaseList([by_id[ref_id] for ref_id in ids if ref_id in by_id], bloc, attr)
        resolved._dereferenced = True
        bloc._data[attr] = resolved


def purge_blocs_references(ref_field, obj_id):
    """Remove references to a deleted object from all blocs in Post and Site.

    A reference can live both at the top level of a blocs field and nested inside an
    accordion (`AccordionListBloc.items[].content[]`), so both depths are purged.
    Accordions cannot themselves be nested (see `BLOCS_DISALLOWED_IN_ACCORDION`), so
    two levels are enough.
    """
    from udata.core.post.models import Post
    from udata.core.site.models import Site

    def purge(collection, blocs_field):
        # Top-level blocs: <blocs_field>[].<ref_field>
        collection.update_many(
            {f"{blocs_field}.{ref_field}": obj_id},
            {"$pull": {f"{blocs_field}.$[b].{ref_field}": obj_id}},
            array_filters=[{f"b.{ref_field}": obj_id}],
        )
        # Blocs nested in an accordion: <blocs_field>[].items[].content[].<ref_field>
        collection.update_many(
            {f"{blocs_field}.items.content.{ref_field}": obj_id},
            {"$pull": {f"{blocs_field}.$[b].items.$[].content.$[c].{ref_field}": obj_id}},
            array_filters=[
                {f"b.items.content.{ref_field}": obj_id},
                {f"c.{ref_field}": obj_id},
            ],
        )

    purge(Post._get_collection(), "blocs")
    for blocs_field in SITE_BLOCS_FIELDS:
        purge(Site._get_collection(), blocs_field)
