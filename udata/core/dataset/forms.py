from urllib.parse import urlparse

from flask import current_app

from udata.forms import ModelForm, fields, validators
from udata.i18n import lazy_gettext as _

from udata.core.storages import resources
from udata.core.spatial.forms import SpatialCoverageField

from .models import (
    Dataset, Resource, License, Checksum, CommunityResource,
    UPDATE_FREQUENCIES, DEFAULT_FREQUENCY, RESOURCE_FILETYPES, CHECKSUM_TYPES,
    LEGACY_FREQUENCIES, RESOURCE_TYPES, TITLE_SIZE_LIMIT, DESCRIPTION_SIZE_LIMIT,
    ResourceSchema,
)

__all__ = ('DatasetForm', 'ResourceForm', 'CommunityResourceForm')


class ChecksumForm(ModelForm):
    model_class = Checksum
    choices = list(zip(CHECKSUM_TYPES, CHECKSUM_TYPES))
    type = fields.SelectField(choices=choices, default='sha1')
    value = fields.StringField(_('Checksum value'), [validators.DataRequired()])


def normalize_format(data):
    '''Normalize format field: strip and lowercase'''
    if data:
        return data.strip().lower()


def enforce_allowed_schemas(form, field):
    schema = field.data
    if schema:
        allowed_schemas = [s['id'] for s in ResourceSchema.objects()]
        if schema.get('name') not in allowed_schemas:
            message = _('Schema name "{schema}" is not an allowed value. Allowed values: {values}')
            raise validators.ValidationError(message.format(
                schema=schema.get('name'),
                values=', '.join(allowed_schemas)
            ))
        
        schema_versions = [d['versions'] for d in ResourceSchema.objects() if d['id'] == schema.get('name')]
        allowed_versions = schema_versions[0] if schema_versions else []
        allowed_versions.append('latest')
        if 'version' in schema:
            if schema.get('version') not in allowed_versions:
                message = _('Version "{version}" is not an allowed value. Allowed values: {values}')
                raise validators.ValidationError(message.format(
                    version=schema.get('version'),
                    values=', '.join(allowed_versions)
                ))
        properties = ['name', 'version']
        for prop in schema:
            if prop not in properties:
                message = _('Sub-property "{prop}" is not allowed value in schema field. Allowed values is : {properties}')
                raise validators.ValidationError(message.format(
                    prop=prop,
                    properties=', '.join(properties),
                ))


class BaseResourceForm(ModelForm):
    title = fields.StringField(
        _('Title'), [validators.DataRequired(), validators.Length(max=TITLE_SIZE_LIMIT)])
    description = fields.MarkdownField(
        _('Description'), [validators.Length(max=DESCRIPTION_SIZE_LIMIT)])
    filetype = fields.RadioField(
        _('File type'), [validators.DataRequired()],
        choices=list(RESOURCE_FILETYPES.items()), default='file',
        description=_('Whether the resource is an uploaded file, '
                      'a remote file or an API'))
    type = fields.RadioField(
        _('Type'), [validators.DataRequired()],
        choices=list(RESOURCE_TYPES.items()), default='other',
        description=_('Resource type (documentation, API...)'))
    url = fields.UploadableURLField(
        _('URL'), [validators.DataRequired()], storage=resources)
    format = fields.StringField(
        _('Format'),
        filters=[normalize_format],
    )
    checksum = fields.FormField(ChecksumForm)
    mime = fields.StringField(
        _('Mime type'),
        description=_('The mime type associated to the extension. '
                      '(ex: text/plain)'))
    filesize = fields.IntegerField(
        _('Size'), [validators.optional()],
        description=_('The file size in bytes'))
    published = fields.DateTimeField(
        _('Publication date'),
        description=_('The publication date of the resource'))
    extras = fields.ExtrasField()
    schema = fields.DictField(
        _('Schema'),
        default={},
        validators=[validators.optional(), enforce_allowed_schemas],
        description=_('The schema slug the resource adheres to'))


class ResourceForm(BaseResourceForm):
    model_class = Resource

    id = fields.UUIDField()


class CommunityResourceForm(BaseResourceForm):
    model_class = CommunityResource

    dataset = fields.DatasetField(_('Related dataset'))
    owner = fields.CurrentUserField()
    organization = fields.PublishAsField(_('Publish as'))


def map_legacy_frequencies(form, field):
    ''' Map legacy frequencies to new ones'''
    if field.data in LEGACY_FREQUENCIES:
        field.data = LEGACY_FREQUENCIES[field.data]


class DatasetForm(ModelForm):
    model_class = Dataset

    title = fields.StringField(
        _('Title'), [validators.DataRequired(), validators.Length(max=TITLE_SIZE_LIMIT)])
    acronym = fields.StringField(_('Acronym'),
                                 description=_('An optional acronym'))
    description = fields.MarkdownField(
        _('Description'), [validators.DataRequired(), validators.Length(max=DESCRIPTION_SIZE_LIMIT)],
        description=_('The details about the dataset '
                      '(collection process, specifics...).'))
    license = fields.ModelSelectField(
        _('License'), model=License, allow_blank=True)
    frequency = fields.SelectField(
        _('Update frequency'),
        choices=list(UPDATE_FREQUENCIES.items()), default=DEFAULT_FREQUENCY,
        validators=[validators.optional()],
        preprocessors=[map_legacy_frequencies],
        description=_('The frequency at which data are updated.'))
    frequency_date = fields.DateTimeField(_('Expected frequency date'))
    deleted = fields.DateTimeField()
    archived = fields.DateTimeField()
    temporal_coverage = fields.DateRangeField(
        _('Temporal coverage'),
        description=_('The period covered by the data'))
    spatial = SpatialCoverageField(
        _('Spatial coverage'),
        description=_('The geographical area covered by the data.'))
    tags = fields.TagField(_('Tags'), description=_('Some taxonomy keywords'))
    private = fields.BooleanField(
        _('Private'),
        description=_('Restrict the dataset visibility to you or '
                      'your organization only.'))

    owner = fields.CurrentUserField()
    organization = fields.PublishAsField(_('Publish as'))
    extras = fields.ExtrasField()
    resources = fields.NestedModelList(ResourceForm)


class ResourcesListForm(ModelForm):
    model_class = Dataset

    resources = fields.NestedModelList(ResourceForm)
