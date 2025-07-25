from datetime import datetime

from blinker import Signal
from flask import url_for
from mongoengine import Q
from mongoengine.signals import post_save

import udata.core.contact_point.api_fields as contact_api_fields
import udata.core.dataset.api_fields as datasets_api_fields
from udata.api import api, fields
from udata.api_fields import field, function_field, generate_fields
from udata.core.activity.models import Auditable
from udata.core.dataservices.constants import (
    DATASERVICE_ACCESS_AUDIENCE_CONDITIONS,
    DATASERVICE_ACCESS_AUDIENCE_TYPES,
    DATASERVICE_ACCESS_TYPES,
    DATASERVICE_FORMATS,
)
from udata.core.dataset.models import Dataset
from udata.core.linkable import Linkable
from udata.core.metrics.helpers import get_stock_metrics
from udata.core.metrics.models import WithMetrics
from udata.core.owned import Owned, OwnedQuerySet
from udata.i18n import lazy_gettext as _
from udata.models import Discussion, Follow, db
from udata.mongo.errors import FieldValidationError
from udata.uris import cdata_url

# "frequency"
# "harvest"
# "internal"
# "page"
# "quality" # Peut-être pas dans une v1 car la qualité sera probablement calculé différemment
# "datasets" # objet : liste de datasets liés à une API
# "spatial"
# "temporal_coverage"


dataservice_permissions_fields = api.model(
    "DataservicePermissions",
    {
        "delete": fields.Permission(),
        "edit": fields.Permission(),
    },
)


class DataserviceQuerySet(OwnedQuerySet):
    def visible(self):
        return self(archived_at=None, deleted_at=None, private=False)

    def hidden(self):
        return self(db.Q(private=True) | db.Q(deleted_at__ne=None) | db.Q(archived_at__ne=None))

    def filter_by_dataset_pagination(self, datasets: list[Dataset], page: int):
        """Paginate the dataservices on the datasets provided.

        This is a workaround, used (at least) in the catalogs for sites and organizations.
        We paginate those kinda weirdly, on their datasets. So a given organization or site
        catalog will only list a `page_size` number of datasets, but we'd still want to display
        the site's or org's dataservices.
        We can't "double paginate", so instead:
        - only if it's the first page, list all the dataservices that serve no dataset
        - list all the dataservices that serve the datasets in this page
        """
        # We need to add Dataservice to the catalog.
        # In the best world, we want:
        # - Keep the correct number of datasets on the page (if the requested page size is 100, we should have 100 datasets)
        # - Have simple MongoDB queries
        # - Do not duplicate the datasets (each dataset is present once in the catalog)
        # - Do not duplicate the dataservices (each dataservice is present once in the catalog)
        # - Every referenced dataset for one dataservices present on the page (hard to do)
        #
        # Multiple solutions are possible but none check all the constraints.
        # The selected one is to put all the dataservices referencing at least one of the dataset on
        # the page at the end of it. It means dataservices could be duplicated (present on multiple pages)
        # and these dataservices may referenced some datasets not present in the current page. It's working
        # if somebody is doing the same thing as us (keeping the list of all the datasets IDs for the entire catalog then
        # listing all dataservices in a second pass)
        # Another option is to do some tricky Mongo requests to order/group datasets by their presence in some dataservices but
        # it could be really hard to do with a n..n relation.
        # Let's keep this solution simple right now and iterate on it in the future.
        dataservices_filter = Q(datasets__in=[d.id for d in datasets])

        # On the first page, add all dataservices without datasets
        if page == 1:
            dataservices_filter = dataservices_filter | Q(datasets__size=0)

        return self(dataservices_filter)


@generate_fields()
class HarvestMetadata(db.EmbeddedDocument):
    backend = field(db.StringField())
    domain = field(db.StringField())

    source_id = field(db.StringField())
    source_url = field(db.URLField())

    remote_id = field(db.StringField())
    remote_url = field(db.URLField())

    # If the node ID is a `URIRef` it means it links to something external, if it's not an `URIRef` it's often a
    # auto-generated ID just to link multiple RDF node togethers. When exporting as RDF to other catalogs, we
    # want to re-use this node ID (only if it's not auto-generated) to improve compatibility.
    uri = field(
        db.URLField(),
        description="RDF node ID if it's an `URIRef`. `None` if it's not present or if it's a random auto-generated ID inside the graph.",
    )

    created_at = field(
        db.DateTimeField(), description="Date of the creation as provided by the harvested catalog"
    )
    last_update = field(db.DateTimeField(), description="Date of the last harvesting")
    archived_at = field(db.DateTimeField())
    archived_reason = field(db.StringField())


@generate_fields()
class AccessAudience(db.EmbeddedDocument):
    role = field(db.StringField(choices=DATASERVICE_ACCESS_AUDIENCE_TYPES), filterable={})
    condition = field(db.StringField(choices=DATASERVICE_ACCESS_AUDIENCE_CONDITIONS), filterable={})


def check_only_one_condition_per_role(access_audiences, **_kwargs):
    roles = set(e["role"] for e in access_audiences)
    if len(roles) != len(access_audiences):
        raise FieldValidationError(
            _("You can only set one condition for a given access audience role"),
            field="access_audiences",
        )


@generate_fields(
    searchable=True,
    additional_filters={"organization_badge": "organization.badges"},
    additional_sorts=[
        {"key": "followers", "value": "metrics.followers"},
        {"key": "views", "value": "metrics.views"},
    ],
)
class Dataservice(Auditable, WithMetrics, Linkable, Owned, db.Document):
    meta = {
        "indexes": [
            "$title",
            "metrics.followers",
            "metrics.views",
        ]
        + Owned.meta["indexes"],
        "queryset_class": DataserviceQuerySet,
        "auto_create_index_on_save": True,
    }

    after_save = Signal()
    on_create = Signal()
    on_update = Signal()
    on_delete = Signal()

    verbose_name = _("dataservice")

    def __str__(self):
        return self.title or ""

    title = field(
        db.StringField(required=True), example="My awesome API", sortable=True, show_as_ref=True
    )
    acronym = field(
        db.StringField(max_length=128),
    )
    # /!\ do not set directly the slug when creating or updating a dataset
    # this will break the search indexation
    slug = field(
        db.SlugField(
            max_length=255, required=True, populate_from="title", update=True, follow=True
        ),
        readonly=True,
    )
    description = field(db.StringField(default=""), description="In markdown")
    base_api_url = field(db.URLField(), sortable=True)

    machine_documentation_url = field(
        db.URLField(), description="Swagger link, OpenAPI format, WMS XML…"
    )
    technical_documentation_url = field(db.URLField(), description="HTML version of a Swagger…")
    business_documentation_url = field(db.URLField())

    rate_limiting = field(db.StringField())
    rate_limiting_url = field(db.URLField())

    availability = field(db.FloatField(min=0, max=100), example="99.99")
    availability_url = field(db.URLField())

    access_type = field(db.StringField(choices=DATASERVICE_ACCESS_TYPES), filterable={})
    access_audiences = field(
        db.EmbeddedDocumentListField(AccessAudience),
        checks=[check_only_one_condition_per_role],
    )

    authorization_request_url = field(db.URLField())

    format = field(db.StringField(choices=DATASERVICE_FORMATS))

    license = field(
        db.ReferenceField("License"),
        allow_null=True,
        attribute="license.id",
        description="The ID of the license",
    )

    tags = field(
        db.TagListField(),
        filterable={
            "key": "tag",
        },
    )

    private = field(
        db.BooleanField(default=False),
        description="Is the dataservice private to the owner or the organization",
    )

    extras = field(
        db.ExtrasField(),
        auditable=False,
    )

    contact_points = field(
        db.ListField(
            field(
                db.ReferenceField("ContactPoint", reverse_delete_rule=db.PULL),
                nested_fields=contact_api_fields.contact_point_fields,
                allow_null=True,
            ),
        ),
        filterable={
            "key": "contact_point",
        },
    )

    created_at = field(
        db.DateTimeField(verbose_name=_("Creation date"), default=datetime.utcnow, required=True),
        readonly=True,
        sortable="created",
    )
    metadata_modified_at = field(
        db.DateTimeField(
            verbose_name=_("Last modification date"), default=datetime.utcnow, required=True
        ),
        readonly=True,
        sortable="last_modified",
        auditable=False,
    )
    deleted_at = field(db.DateTimeField(), auditable=False)
    archived_at = field(db.DateTimeField())

    datasets = field(
        db.ListField(
            field(
                db.LazyReferenceField(Dataset, passthrough=True),
                nested_fields=datasets_api_fields.dataset_ref_fields,
            )
        ),
        filterable={
            "key": "dataset",
        },
        href=lambda dataservice: url_for(
            "api.datasets", dataservice=dataservice.id, _external=True
        ),
    )

    harvest = field(
        db.EmbeddedDocumentField(HarvestMetadata),
        readonly=True,
        auditable=False,
    )

    @function_field(description="Link to the API endpoint for this dataservice")
    def self_api_url(self, **kwargs):
        return url_for(
            "api.dataservice",
            dataservice=self._link_id(**kwargs),
            **self._self_api_url_kwargs(**kwargs),
        )

    @function_field(description="Link to the udata web page for this dataservice", show_as_ref=True)
    def self_web_url(self, **kwargs):
        return cdata_url(f"/dataservices/{self._link_id(**kwargs)}/", **kwargs)

    __metrics_keys__ = [
        "discussions",
        "discussions_open",
        "followers",
        "followers_by_months",
        "views",
    ]

    @property
    def is_hidden(self):
        return self.private or self.deleted_at or self.archived_at

    @property
    @function_field(
        nested_fields=dataservice_permissions_fields,
    )
    def permissions(self):
        from .permissions import DataserviceEditPermission

        return {
            "delete": DataserviceEditPermission(self),
            "edit": DataserviceEditPermission(self),
        }

    def count_discussions(self):
        self.metrics["discussions"] = Discussion.objects(subject=self).count()
        self.metrics["discussions_open"] = Discussion.objects(subject=self, closed=None).count()
        self.save(signal_kwargs={"ignores": ["post_save"]})

    def count_followers(self):
        self.metrics["followers"] = Follow.objects(until=None).followers(self).count()
        self.metrics["followers_by_months"] = get_stock_metrics(
            Follow.objects(following=self), date_label="since"
        )
        self.save(signal_kwargs={"ignores": ["post_save"]})


post_save.connect(Dataservice.post_save, sender=Dataservice)
