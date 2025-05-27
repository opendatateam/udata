import udata.core.contact_point.api_fields as contact_api_fields
from udata.api_fields import field, function_field, generate_fields
from udata.core.owned import Owned
from udata.i18n import lazy_gettext as _
from udata.mongo import db
from udata.mongo.errors import FieldValidationError
from udata.uris import endpoint_for
from udata.utils import hash_url

from .constants import STANDARD_TYPES, STATUS_TYPES


def check_url_does_not_exists(url, **_kwargs):
    """Ensure a reuse URL is not yet registered"""
    if url and Standard.url_exists(url):
        raise FieldValidationError(_("This URL is already registered"), field="url")


@generate_fields()
class Standard(db.Datetimed, Owned, db.Document):
    name = field(
        db.StringField(required=True),
        sortable=True,
        show_as_ref=True,
    )
    slug = field(
        db.SlugField(max_length=255, required=True, populate_from="name", update=True, follow=True),
        readonly=True,
        auditable=False,
    )
    description = field(
        db.StringField(required=True),
        markdown=True,
    )
    type = field(
        db.StringField(required=True, choices=list(STANDARD_TYPES)),
        filterable={},
    )
    url = field(
        db.URLField(required=True),
        description="The URL to query the schema",
        checks=[check_url_does_not_exists],
    )
    status = field(
        db.StringField(required=True, choices=list(STATUS_TYPES)),
        filterable={},
    )
    tags = field(
        db.TagListField(),
        filterable={
            "key": "tag",
        },
    )
    extras = field(db.ExtrasField(), auditable=False)
    deleted = field(
        db.DateTimeField(),
        auditable=False,
    )
    urlhash = db.StringField(required=True, unique=True)
    archived = field(
        db.DateTimeField(),
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

    verbose_name = _("standard")

    meta = {
        "indexes": [
            "$name",
            "created_at",
            "last_modified",
            "urlhash",
        ]
    }

    def __str__(self):
        return self.name or ""

    @function_field(description="Link to the API endpoint for this report")
    def self_api_url(self):
        return endpoint_for("api.report", report=self, _external=True)

    @classmethod
    def url_exists(cls, url):
        urlhash = hash_url(url)
        return cls.objects(urlhash=urlhash).count() > 0

    @classmethod
    def get(cls, id_or_slug):
        obj = cls.objects(slug=id_or_slug).first()
        return obj or cls.objects.get_or_404(id=id_or_slug)

    @property
    def type_label(self):
        return STANDARD_TYPES[self.type]

    def clean(self):
        super(Standard, self).clean()
        """Auto populate urlhash from url"""
        if not self.urlhash or "url" in self._get_changed_fields():
            self.urlhash = hash_url(self.url)
