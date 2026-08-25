import copy

from udata.core.access_type.constants import (
    AccessAudienceCondition,
    AccessAudienceType,
    AccessType,
    InspireLimitationCategory,
)
from udata.core.access_type.models import AccessAudience
from udata.core.spatial.forms import SpatialCoverageField
from udata.forms import ModelForm, fields, validators
from udata.i18n import lazy_gettext as _
from udata.mongo.errors import FieldValidationError

from .constants import (
    CHECKSUM_TYPES,
    DESCRIPTION_SHORT_SIZE_LIMIT,
    DESCRIPTION_SIZE_LIMIT,
    RESOURCE_FILETYPES,
    RESOURCE_TYPES,
    TITLE_SIZE_LIMIT,
    UpdateFrequency,
)
from .models import (
    Checksum,
    CommunityResource,
    Dataset,
    License,
    Resource,
    Schema,
)
from .permissions import can_write_extra, sanitize_reserved_extras

__all__ = ("DatasetForm", "ResourceForm", "CommunityResourceForm")

# Fields computed by the server at upload time for resources hosted on our
# file storage (see `handle_upload`). They must not be overridden by API
# clients: a client sending stale metadata (e.g. fetched before a new file
# upload) would otherwise overwrite the values describing the currently hosted
# file. None of these fields are editable from the admin front for a hosted
# file: they are only sent for `remote` resources.
# Same reasoning as the `url` protection from
# https://github.com/opendatateam/udata/issues/2544
HOSTED_RESOURCE_PROTECTED_FIELDS = (
    "filetype",
    "url",
    "checksum",
    "filesize",
    "mime",
    "format",
)


class ReservedExtrasField(fields.ExtrasField):
    """An extras field that keeps platform-reserved keys out of non-sysadmin writes.

    Both hooks are needed because the two write paths differ. A creation never
    calls `populate_obj`: `ModelForm.save()` builds the model straight from the
    form data, so the reserved keys have to be dropped from `self.data` itself.
    An update, on the other hand, replaces the whole extras dict, and would drop
    the reserved keys a payload does not echo back — hence the merge with the
    stored values.
    """

    def process_formdata(self, valuelist):
        super().process_formdata(valuelist)
        data = self.data or {}
        self.data = {key: value for key, value in data.items() if can_write_extra(key)}

    def populate_obj(self, obj, name):
        setattr(obj, name, sanitize_reserved_extras(getattr(obj, name), self.data or {}))


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
    url = fields.URLField(_("URL"), [validators.DataRequired()])
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
    extras = ReservedExtrasField()
    schema = fields.FormField(SchemaForm)

    def populate_obj(self, obj):
        # Only protect existing hosted files: a brand new resource has no url
        # yet and must be populated normally. `checksum` is deep-copied because
        # populate_obj mutates the existing embedded document in place.
        protect = obj.filetype == "file" and obj.url
        protected_values = (
            {name: copy.deepcopy(getattr(obj, name)) for name in HOSTED_RESOURCE_PROTECTED_FIELDS}
            if protect
            else {}
        )
        super().populate_obj(obj)
        for name, value in protected_values.items():
            setattr(obj, name, value)


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


def unmarshal_frequency(form, field):
    if field.data is None:
        return
    # We don't need to worry about invalid field.data being fed to UpdateFrequency here,
    # since the API will already have ensured incoming data matches the field definition,
    # which in our case is an enum of valid UpdateFrequency values.
    field.data = UpdateFrequency(field.data)


class AccessAudienceForm(ModelForm):
    model_class = AccessAudience

    role = fields.SelectField(choices=[(e.value, e.value) for e in AccessAudienceType])
    condition = fields.SelectField(choices=[(e.value, e.value) for e in AccessAudienceCondition])


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
    description_short = fields.StringField(
        _("Short description"),
        [validators.Length(max=DESCRIPTION_SHORT_SIZE_LIMIT)],
        description=_("A short description of the dataset."),
    )
    license = fields.ModelSelectField(_("License"), model=License, allow_blank=True)
    access_type = fields.SelectField(
        choices=[(e.value, e.value) for e in AccessType],
        default=AccessType.OPEN,
        validators=[validators.optional()],
    )
    access_audiences = fields.NestedModelList(AccessAudienceForm)
    authorization_request_url = fields.StringField(_("Authorization request URL"))
    access_type_reason_category = fields.SelectField(
        _("Access type reason category"),
        choices=[(e.value, e.label) for e in InspireLimitationCategory],
        validators=[validators.optional()],
    )
    access_type_reason = fields.StringField(_("Access type reason"))
    frequency = fields.SelectField(
        _("Update frequency"),
        choices=list(UpdateFrequency),
        default=UpdateFrequency.UNKNOWN,
        validators=[validators.optional()],
        # Unmarshaling should not happen during validation, but flask-restx makes it cumbersome
        # to do it earlier, requiring a request parser (unmarshaler) separate from the marshaler,
        # meaning we can't use the same object for @api.expect and @api.marshal_with.
        # This should get better once flask-restx moves to something like marshmallow, which
        # handles marshaling/unmarshaling more symmetrically and in the same object.
        preprocessors=[unmarshal_frequency],
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
    extras = ReservedExtrasField()
    resources = fields.NestedModelList(ResourceForm)
    contact_points = fields.ContactPointListField()


class ResourcesListForm(ModelForm):
    model_class = Dataset

    resources = fields.NestedModelList(ResourceForm)
