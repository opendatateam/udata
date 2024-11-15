from datetime import datetime

from flask import url_for
from mongoengine import Q

import udata.core.contact_point.api_fields as contact_api_fields
import udata.core.dataset.api_fields as datasets_api_fields
from udata.api_fields import field, function_field, generate_fields
from udata.core.dataset.models import Dataset
from udata.core.metrics.models import WithMetrics
from udata.core.owned import Owned, OwnedQuerySet
from udata.i18n import lazy_gettext as _
from udata.models import Discussion, Follow, db
from udata.uris import endpoint_for

# "frequency"
# "harvest"
# "internal"
# "page"
# "quality" # Peut-être pas dans une v1 car la qualité sera probablement calculé différemment
# "datasets" # objet : liste de datasets liés à une API
# "spatial"
# "temporal_coverage"

DATASERVICE_FORMATS = ["REST", "WMS", "WSL"]


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


@generate_fields(
    searchable=True,
    additional_filters={"organization_badge": "organization.badges"},
)
class Dataservice(WithMetrics, Owned, db.Document):
    meta = {
        "indexes": [
            "$title",
        ]
        + Owned.meta["indexes"],
        "queryset_class": DataserviceQuerySet,
        "auto_create_index_on_save": True,
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
        db.SlugField(
            max_length=255, required=True, populate_from="title", update=True, follow=True
        ),
        readonly=True,
    )
    description = field(db.StringField(default=""), description="In markdown")
    base_api_url = field(db.URLField(), sortable=True)
    endpoint_description_url = field(db.URLField())
    business_documentation_url = field(db.URLField())
    authorization_request_url = field(db.URLField())
    availability = field(db.FloatField(min=0, max=100), example="99.99")
    rate_limiting = field(db.StringField())
    is_restricted = field(db.BooleanField(), filterable={})
    has_token = field(db.BooleanField())
    format = field(db.StringField(choices=DATASERVICE_FORMATS))

    license = field(
        db.ReferenceField("License"),
        allow_null=True,
        attribute="license.id",
        description="The ID of the license",
    )

    tags = field(
        db.TagListField(),
    )

    private = field(
        db.BooleanField(default=False),
        description="Is the dataservice private to the owner or the organization",
    )

    extras = field(db.ExtrasField())

    contact_point = field(
        db.ReferenceField("ContactPoint", reverse_delete_rule=db.NULLIFY),
        nested_fields=contact_api_fields.contact_point_fields,
        allow_null=True,
    )

    created_at = field(
        db.DateTimeField(verbose_name=_("Creation date"), default=datetime.utcnow, required=True),
        readonly=True,
    )
    metadata_modified_at = field(
        db.DateTimeField(
            verbose_name=_("Last modification date"), default=datetime.utcnow, required=True
        ),
        readonly=True,
    )
    deleted_at = field(db.DateTimeField())
    archived_at = field(db.DateTimeField(), readonly=True)

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
    )

    @function_field(description="Link to the API endpoint for this dataservice")
    def self_api_url(self):
        return endpoint_for("api.dataservice", dataservice=self, _external=True)

    @function_field(description="Link to the udata web page for this dataservice")
    def self_web_url(self):
        return endpoint_for("dataservices.show", dataservice=self, _external=True)

    # TODO
    # frequency = db.StringField(choices=list(UPDATE_FREQUENCIES.keys()))
    # temporal_coverage = db.EmbeddedDocumentField(db.DateRange)
    # spatial = db.EmbeddedDocumentField(SpatialCoverage)
    # harvest = db.EmbeddedDocumentField(HarvestDatasetMetadata)

    @property
    def is_hidden(self):
        return self.private or self.deleted_at or self.archived_at

    def count_discussions(self):
        self.metrics["discussions"] = Discussion.objects(subject=self, closed=None).count()
        self.save()

    def count_followers(self):
        self.metrics["followers"] = Follow.objects(until=None).followers(self).count()
        self.save()
