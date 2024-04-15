from datetime import datetime
from udata.api_fields import field, generate_fields
from udata.core.badges.models import BadgeMixin
from udata.core.dataset.models import Dataset
from udata.core.metrics.models import WithMetrics
from udata.core.owned import Owned
from udata.i18n import lazy_gettext as _
import udata.core.contact_point.api_fields as contact_api_fields
import udata.core.dataset.api_fields as datasets_api_fields

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


@generate_fields(mask=','.join(('id', 'title')))
class Dataservice(WithMetrics, BadgeMixin, Owned, db.Document):
    title = field(
        db.StringField(required=True),
        example="My awesome API",
        sortable=True,
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
    base_api_url = field(
        db.URLField(required=True),
        sortable=True,
    )
    endpoint_description_url = field(db.URLField())
    authorization_request_url = field(db.URLField())
    availability= field(
        db.FloatField(min=0, max=100),
        example='99.99'
    )
    rate_limiting = field(db.StringField())
    is_restricted = field(db.BooleanField())
    has_token = field(db.BooleanField())
    format = field(db.StringField(choices=DATASERVICE_FORMATS))

    license = field(db.ReferenceField('License'))

    tags = field(
        db.TagListField(),
    )

    private = field(
        db.BooleanField(default=False),
        description='Is the dataservice private to the owner or the organization'
    )
    
    extras = field(db.ExtrasField())

    contact_point = field(
        db.ReferenceField('ContactPoint', reverse_delete_rule=db.NULLIFY),
        nested_fields=contact_api_fields.contact_point_fields,
    )

    created_at = field(
        db.DateTimeField(verbose_name=_('Creation date'), default=datetime.utcnow, required=True),
        readonly=True,
    )
    metadata_modified_at = field(
        db.DateTimeField(verbose_name=_('Last modification date'), default=datetime.utcnow, required=True),
        readonly=True,
    )
    deleted_at = field(db.DateTimeField(), readonly=True)
    archived_at = field(db.DateTimeField(), readonly=True)

    datasets = field(
        db.ListField(
            field(
                db.ReferenceField(Dataset),
                nested_fields=datasets_api_fields.dataset_fields,
            )
        )
    )

    # TODO
    # frequency = db.StringField(choices=list(UPDATE_FREQUENCIES.keys()))
    # temporal_coverage = db.EmbeddedDocumentField(db.DateRange)
    # spatial = db.EmbeddedDocumentField(SpatialCoverage)
    # harvest = db.EmbeddedDocumentField(HarvestDatasetMetadata)
