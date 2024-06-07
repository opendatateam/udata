from datetime import datetime
from udata.api_fields import field, function_field, generate_fields
from udata.core.dataset.models import Dataset
from udata.core.metrics.models import WithMetrics
from udata.core.owned import Owned, OwnedQuerySet
import udata.core.contact_point.api_fields as contact_api_fields
import udata.core.dataset.api_fields as datasets_api_fields
from udata.i18n import lazy_gettext as _

from udata.models import db, Discussion, Follow
from udata.uris import endpoint_for

# "frequency"
# "harvest"
# "internal"
# "page"
# "quality" # Peut-être pas dans une v1 car la qualité sera probablement calculé différemment
# "datasets" # objet : liste de datasets liés à une API
# "spatial"
# "temporal_coverage"

DATASERVICE_FORMATS = ['REST', 'WMS', 'WSL']


class DataserviceQuerySet(OwnedQuerySet):
    def visible(self):
        return self(archived_at=None, deleted_at=None, private=False)

    def hidden(self):
        return self(db.Q(private=True) |
                    db.Q(deleted_at__ne=None) |
                    db.Q(archived_at__ne=None))

@generate_fields()
class Dataservice(WithMetrics, Owned, db.Document):
    meta = {
        'indexes': [
            '$title',
        ] + Owned.meta['indexes'],
        'queryset_class': DataserviceQuerySet,
        'auto_create_index_on_save': True
    }

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

    license = field(
        db.ReferenceField('License'),
        allow_null=True,
    )

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
        allow_null=True,
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

    @function_field(description="Link to the API endpoint for this dataservice")
    def self_api_url(self):
        return endpoint_for('api.dataservice', dataservice=self, _external=True)

    def self_web_url():
        pass

    # TODO
    # frequency = db.StringField(choices=list(UPDATE_FREQUENCIES.keys()))
    # temporal_coverage = db.EmbeddedDocumentField(db.DateRange)
    # spatial = db.EmbeddedDocumentField(SpatialCoverage)
    # harvest = db.EmbeddedDocumentField(HarvestDatasetMetadata)

    @property
    def is_hidden(self):
        return self.private or self.deleted_at or self.archived_at

    def count_discussions(self):
        self.metrics['discussions'] = Discussion.objects(subject=self, closed=None).count()
        self.save()

    def count_followers(self):
        self.metrics['followers'] = Follow.objects(until=None).followers(self).count()
        self.save()
