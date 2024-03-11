from datetime import datetime
from udata.core.badges.models import BadgeMixin
from udata.core.metrics.models import WithMetrics
from udata.i18n import lazy_gettext as _
from udata.api import api, fields
import udata.core.contact_point.api_fields as contact_api_fields

from udata.models import db

# "frequency"
# "harvest"
# "internal"
# "page"
# "quality" # Peut-être pas dans une v1 car la qualité sera probablement calculé différemment
# "datasets" # objet : liste de datasets liés à une API
# "spatial"
# "temporal_coverage"

DATASERVICE_FORMATS = ['REST', 'WMS', 'WSL']

def generate_fields(cls):
    document_keys = set(dir(db.Document))
    keys = [key for key in cls.__dict__.keys() if key not in document_keys]

    cls_fields = {}

    for key in keys:
        if key == 'objects': continue

        field = getattr(cls, key)
        if not hasattr(field, '__additional_field_info__'): continue 

        params = {}
        params['required'] = field.required

        if field.__additional_field_info__.get('convert_to'):
            constructor = field.__additional_field_info__.get('convert_to')
        elif isinstance(field, db.StringField):
            constructor = fields.String
            params['min_length'] = field.min_length
            params['max_length'] = field.max_length
        elif isinstance(field, db.FloatField):
            constructor = fields.Float
            params['min'] = field.min
            params['max'] = field.max
        elif isinstance(field, db.BooleanField):
            constructor = fields.Boolean
        elif isinstance(field, db.DateTimeField):
            constructor = fields.ISODateTime
        elif isinstance(field, db.DictField):
            constructor = fields.Raw
        elif isinstance(field, db.ListField):
            nested_field = field.__additional_field_info__.get('nested_field')
            if nested_field is None:
                raise ValueError(f"List field for '{key}' should have a `nested_field` argument")

            constructor = lambda **kwargs: fields.List(nested_field, **kwargs)
        elif isinstance(field, db.ReferenceField):
            nested_field = field.__additional_field_info__.get('nested_field')
            if nested_field is None:
                raise ValueError(f"Reference field for '{key}' should have a `nested_field` argument")

            constructor = lambda **kwargs: fields.Nested(nested_field, **kwargs)
        else:
            raise ValueError(f"Unsupported MongoEngine field type {field.__class__.__name__}")

        params = {**params, **field.__additional_field_info__}
        cls_fields[key] = constructor(**params)

    cls.__fields__ = api.model(cls.__name__, cls_fields)
    return cls

def field(inner, **kwargs):
    inner.__additional_field_info__ = kwargs
    return inner

@generate_fields
class Dataservice(WithMetrics, BadgeMixin, db.Owned, db.Document):
    title = field(
        db.StringField(required=True),
        example="My awesome API",
    )
    acronym = field(
        db.StringField(max_length=128),
    )
    # /!\ do not set directly the slug when creating or updating a dataset
    # this will break the search indexation
    slug = field(
        db.SlugField(max_length=255, required=True, populate_from='title', update=True, follow=True),
        readonly=True,
    )
    description = field(
        db.StringField(default=''),
        description="In markdown"
    )
    uri = field(db.URLField(required=True))
    endpoint_description = field(db.URLField())
    authorization_request_url = field(db.URLField())
    availability= field(
        db.FloatField(min=0, max=100),
        example='99.99'
    )
    rate_limiting = field(db.StringField())
    is_restricted = field(db.BooleanField())
    has_token = field(db.BooleanField())
    format = field(db.StringField(choices=DATASERVICE_FORMATS))

    license = field(
        db.ReferenceField('License'),
        convert_to=fields.String,
    )

    tags = field(
        db.TagListField(),
        nested_field=fields.String,
    )

    private = field(
        db.BooleanField(default=False),
        description='Is the dataservice private to the owner or the organization'
    )
    
    extras = field(db.ExtrasField())

    contact_point = field(
        db.ReferenceField('ContactPoint', reverse_delete_rule=db.NULLIFY),
        nested_field=contact_api_fields.contact_point_fields,
        readonly=True
    )

    created_at = field(
        db.DateTimeField(verbose_name=_('Creation date'), default=datetime.utcnow, required=True),
        readonly=True,
    )
    modified_at = field(
        db.DateTimeField(verbose_name=_('Last modification date'), default=datetime.utcnow, required=True),
        readonly=True,
    )
    deleted_at = field(db.DateTimeField(), readonly=True)
    archived_at = field(db.DateTimeField(), readonly=True)

    # TODO
    # frequency = db.StringField(choices=list(UPDATE_FREQUENCIES.keys()))
    # temporal_coverage = db.EmbeddedDocumentField(db.DateRange)
    # spatial = db.EmbeddedDocumentField(SpatialCoverage)
    # harvest = db.EmbeddedDocumentField(HarvestDatasetMetadata)
