from udata.core.spatial.forms import SpatialCoverageField
from udata.core.storages import resources
from udata.forms import ModelForm, fields, validators
from udata.i18n import lazy_gettext as _
from udata.mongo.errors import FieldValidationError

from .constants import (
    CHECKSUM_TYPES,
    DEFAULT_FREQUENCY,
    DESCRIPTION_SIZE_LIMIT,
    LEGACY_FREQUENCIES,
    RESOURCE_FILETYPES,
    RESOURCE_TYPES,
    TITLE_SIZE_LIMIT,
    UPDATE_FREQUENCIES,
)
from .models import (
    Checksum,
    CommunityResource,
    Dataset,
    License,
    Resource,
    Schema,
)

__all__ = ("DatasetForm", "ResourceForm", "CommunityResourceForm")


class ChecksumForm(ModelForm):
    model_class = Checksum
    choices = list(zip(CHECKSUM_TYPES, CHECKSUM_TYPES))
    type = fields.SelectField(choices=choices, default="sha1")
    value = fields.StringField(_("Checksum value"), [validators.DataRequired()])


def normalize_format(data):
    """Normalize format field: strip and lowercase"""
    if data:
        return data.strip().lower()


class SchemaForm(ModelForm):
    model_class = Schema
    url = fields.URLField(_("URL of the schema"))
    name = fields.StringField(_("Name of the schema"))
    version = fields.StringField(_("Version of the schema"))

    def validate(self, extra_validators=None):
        validation = super().validate(extra_validators)

        try:
            Schema(url=self.url.data, name=self.name.data, version=self.version.data).clean(
                check_schema_in_catalog=True
            )
        except FieldValidationError as err:
            field = getattr(self, err.field)
            field.errors.append(str(err))
            return False

        return validation


class BaseResourceForm(ModelForm):
    title = fields.StringField(
        _("Title"), [validators.DataRequired(), validators.Length(max=TITLE_SIZE_LIMIT)]
    )
    description = fields.MarkdownField(
        _("Description"), [validators.Length(max=DESCRIPTION_SIZE_LIMIT)]
    )
    filetype = fields.RadioField(
        _("File type"),
        [validators.DataRequired()],
        choices=list(RESOURCE_FILETYPES.items()),
        default="file",
        description=_("Whether the resource is an uploaded file, a remote file or an API"),
    )
    type = fields.RadioField(
        _("Type"),
        [validators.DataRequired()],
        choices=list(RESOURCE_TYPES.items()),
        default="other",
        description=_("Resource type (documentation, API...)"),
    )
    url = fields.UploadableURLField(_("URL"), [validators.DataRequired()], storage=resources)
    format = fields.StringField(
        _("Format"),
        filters=[normalize_format],
    )
    checksum = fields.FormField(ChecksumForm)
    mime = fields.StringField(
        _("Mime type"),
        description=_("The mime type associated to the extension. (ex: text/plain)"),
    )
    filesize = fields.IntegerField(
        _("Size"), [validators.optional()], description=_("The file size in bytes")
    )
    extras = fields.ExtrasField()
    schema = fields.FormField(SchemaForm)


class ResourceForm(BaseResourceForm):
    model_class = Resource

    id = fields.UUIDField()


class ResourceFormWithoutId(BaseResourceForm):
    model_class = Resource


class CommunityResourceForm(BaseResourceForm):
    model_class = CommunityResource

    dataset = fields.DatasetField(_("Related dataset"))
    owner = fields.CurrentUserField()
    organization = fields.PublishAsField(_("Publish as"))


def map_legacy_frequencies(form, field):
    """Map legacy frequencies to new ones"""
    if field.data in LEGACY_FREQUENCIES:
        field.data = LEGACY_FREQUENCIES[field.data]


def validate_contact_point(form, field):
    """Validates contact point with dataset's org or owner"""
    from udata.models import ContactPoint

    for contact_point in field.data or []:
        if form.organization.data:
            contact_point = ContactPoint.objects(
                id=contact_point.id, organization=form.organization.data
            ).first()
        elif form.owner.data:
            contact_point = ContactPoint.objects(id=contact_point.id, owner=form.owner.data).first()
        if not contact_point:
            raise validators.ValidationError(
                _("Wrong contact point id or contact point ownership mismatch")
            )


class DatasetForm(ModelForm):
    model_class = Dataset

    title = fields.StringField(
        _("Title"), [validators.DataRequired(), validators.Length(max=TITLE_SIZE_LIMIT)]
    )
    acronym = fields.StringField(_("Acronym"), description=_("An optional acronym"))
    description = fields.MarkdownField(
        _("Description"),
        [validators.DataRequired(), validators.Length(max=DESCRIPTION_SIZE_LIMIT)],
        description=_("The details about the dataset (collection process, specifics...)."),
    )
    license = fields.ModelSelectField(_("License"), model=License, allow_blank=True)
    frequency = fields.SelectField(
        _("Update frequency"),
        choices=list(UPDATE_FREQUENCIES.items()),
        default=DEFAULT_FREQUENCY,
        validators=[validators.optional()],
        preprocessors=[map_legacy_frequencies],
        description=_("The frequency at which data are updated."),
    )
    frequency_date = fields.DateTimeField(_("Expected frequency date"))
    deleted = fields.DateTimeField()
    archived = fields.DateTimeField()
    temporal_coverage = fields.DateRangeField(
        _("Temporal coverage"), description=_("The period covered by the data")
    )
    spatial = SpatialCoverageField(
        _("Spatial coverage"), description=_("The geographical area covered by the data.")
    )
    tags = fields.TagField(_("Tags"), description=_("Some taxonomy keywords"))
    private = fields.BooleanField(
        _("Private"),
        description=_("Restrict the dataset visibility to you or your organization only."),
    )

    owner = fields.CurrentUserField()
    organization = fields.PublishAsField(_("Publish as"))
    extras = fields.ExtrasField()
    resources = fields.NestedModelList(ResourceForm)
    contact_points = fields.ContactPointListField(validators=[validate_contact_point])


class ResourcesListForm(ModelForm):
    model_class = Dataset

    resources = fields.NestedModelList(ResourceForm)
