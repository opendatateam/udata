from udata.api import api, fields, base_reference
from udata.i18n import lazy_gettext as _
from udata.core.badges.api import badge_fields
from udata.core.organization.api_fields import org_ref_fields
from udata.core.spatial.api_fields import spatial_coverage_fields
from udata.core.user.api_fields import user_ref_fields

from .models import (
    UPDATE_FREQUENCIES, RESOURCE_FILETYPES, DEFAULT_FREQUENCY,
    CHECKSUM_TYPES, DEFAULT_CHECKSUM_TYPE, DEFAULT_LICENSE, RESOURCE_TYPES
)

checksum_fields = api.model('Checksum', {
    'type': fields.String(
        description=_('The hashing algorithm used to compute the checksum'),
        default=DEFAULT_CHECKSUM_TYPE, enum=CHECKSUM_TYPES),
    'value': fields.String(description=_('The resulting checksum/hash'),
                           required=True)
})

license_fields = api.model('License', {
    'id': fields.String(description=_('The license identifier'), required=True),
    'title': fields.String(description=_('The resource title'), required=True),
    'maintainer': fields.String(description=_('The license official maintainer')),
    'url': fields.String(description=_('The license official URL')),
    'flags': fields.List(fields.String, description=_('Some arbitry flags')),
    'alternate_urls': fields.List(
        fields.String,
        description=_('Same alternative known URLs (improve rematch)')
    ),
    'alternate_titles': fields.List(
        fields.String,
        description=_('Same alternative known titles (improve rematch)')
    ),
})

frequency_fields = api.model('Frequency', {
    'id': fields.String(description=_('The frequency identifier')),
    'label': fields.String(description=_('The frequency display name'))
})

resource_fields = api.model('Resource', {
    'id': fields.String(description=_('The resource unique ID'), readonly=True),
    'title': fields.String(description=_('The resource title'), required=True),
    'description': fields.Markdown(
        description=_('The resource markdown description')),
    'filetype': fields.String(
        description=(_('Whether the resource is an uploaded file'),
                     _('a remote file or an API')),
        required=True, enum=list(RESOURCE_FILETYPES)),
    'type': fields.String(
        description=(_('Resource type (documentation, API...)')),
        required=True, enum=list(RESOURCE_TYPES)),
    'format': fields.String(description=_('The resource format'), required=True),
    'url': fields.String(description=_('The resource URL'), required=True),
    'latest': fields.String(description=_('The permanent URL redirecting to '
                            'the latest version of the resource. When the '
                            'resource data is updated, the URL will '
                            'change, the latest URL won\'t.'),
                            readonly=True),
    'checksum': fields.Nested(
        checksum_fields, allow_null=True,
        description=_('A checksum to validate file validity')),
    'filesize': fields.Integer(description=_('The resource file size in bytes')),
    'mime': fields.String(description=_('The resource mime type')),
    'created_at': fields.ISODateTime(
        readonly=True, description=_('The resource creation date')),
    'published': fields.ISODateTime(
        description=_('The resource publication date')),
    'last_modified': fields.ISODateTime(
        attribute='modified', readonly=True,
        description=_('The resource last modification date')),
    'metrics': fields.Raw(
        description=_('The resource metrics'), readonly=True),
    'extras': fields.Raw(description=_('Extra attributes as key-value pairs')),
    'preview_url': fields.String(description=_('An optional preview URL to be '
                                 'loaded as a standalone page (ie. iframe or '
                                 'new page)'),
                                 readonly=True),
    'schema': fields.Raw(description=_('Reference to the associated schema'), readonly=True),
})

upload_fields = api.inherit('UploadedResource', resource_fields, {
    'success': fields.Boolean(
        description=_('Whether the upload succeeded or not.'),
        readonly=True, default=True),
})

resources_order = api.as_list(fields.String(description=_('Resource ID')))

temporal_coverage_fields = api.model('TemporalCoverage', {
    'start': fields.ISODateTime(description=_('The temporal coverage start date'),
                                required=True),
    'end': fields.ISODateTime(description=_('The temporal coverage end date'),
                              required=True),
})

dataset_ref_fields = api.inherit('DatasetReference', base_reference, {
    'title': fields.String(description=_('The dataset title'), readonly=True),
    'acronym': fields.String(description=_('An optional dataset acronym'),
                             readonly=True),
    'uri': fields.UrlFor(
        'api.dataset', lambda d: {'dataset': d},
        description=_('The API URI for this dataset'), readonly=True),
    'page': fields.UrlFor(
        'datasets.show', lambda d: {'dataset': d},
        description=_('The web page URL for this dataset'), readonly=True, fallback_endpoint='api.dataset'),
})

community_resource_fields = api.inherit('CommunityResource', resource_fields, {
    'dataset': fields.Nested(
        dataset_ref_fields, allow_null=True,
        description=_('Reference to the associated dataset')),
    'organization': fields.Nested(
        org_ref_fields, allow_null=True,
        description=_('The producer organization')),
    'owner': fields.Nested(
        user_ref_fields, allow_null=True,
        description=_('The user information'))
})

community_resource_page_fields = api.model(
    'CommunityResourcePage', fields.pager(community_resource_fields))

#: Default mask to make it lightweight by default
DEFAULT_MASK = ','.join((
    'id', 'title', 'acronym', 'slug', 'description', 'created_at', 'last_modified', 'deleted',
    'private', 'tags', 'badges', 'resources', 'frequency', 'frequency_date', 'extras',
    'metrics', 'organization', 'owner', 'temporal_coverage', 'spatial', 'license',
    'uri', 'page', 'last_update', 'archived'
))

dataset_fields = api.model('Dataset', {
    'id': fields.String(description=_('The dataset identifier'), readonly=True),
    'title': fields.String(description=_('The dataset title'), required=True),
    'acronym': fields.String(description=_('An optional dataset acronym')),
    'slug': fields.String(
        description=_('The dataset permalink string'), required=True),
    'description': fields.Markdown(
        description=_('The dataset description in markdown'), required=True),
    'created_at': fields.ISODateTime(
        description=_('The dataset creation date'), required=True),
    'last_modified': fields.ISODateTime(
        description=_('The dataset last modification date'), required=True),
    'deleted': fields.ISODateTime(description=_('The deletion date if deleted')),
    'archived': fields.ISODateTime(description=_('The archival date if archived')),
    'featured': fields.Boolean(description=_('Is the dataset featured')),
    'private': fields.Boolean(
        description=_('Is the dataset private to the owner or the organization')),
    'tags': fields.List(fields.String),
    'badges': fields.List(fields.Nested(badge_fields),
                          description=_('The dataset badges'),
                          readonly=True),
    'resources': fields.List(
        fields.Nested(resource_fields, description=_('The dataset resources'))),
    'community_resources': fields.List(
        fields.Nested(
            community_resource_fields,
            description=_('The dataset community submitted resources'))),
    'frequency': fields.String(
        description=_('The update frequency'), required=True,
        enum=list(UPDATE_FREQUENCIES), default=DEFAULT_FREQUENCY),
    'frequency_date': fields.ISODateTime(
        description=(_('Next expected update date, you will be notified '
                     'once that date is reached.'))),
    'extras': fields.Raw(description=_('Extra attributes as key-value pairs')),
    'metrics': fields.Raw(attribute=lambda o: o.get_metrics(), description=_('The dataset metrics')),
    'organization': fields.Nested(
        org_ref_fields, allow_null=True,
        description=_('The producer organization')),
    'owner': fields.Nested(
        user_ref_fields, allow_null=True, description=_('The user information')),
    'temporal_coverage': fields.Nested(
        temporal_coverage_fields, allow_null=True,
        description=_('The temporal coverage')),
    'spatial': fields.Nested(
        spatial_coverage_fields, allow_null=True,
        description=_('The spatial coverage')),
    'license': fields.String(attribute='license.id',
                             default=DEFAULT_LICENSE['id'],
                             description=_('The dataset license')),
    'uri': fields.UrlFor(
        'api.dataset', lambda o: {'dataset': o},
        description=_('The dataset API URI'), required=True),
    'page': fields.UrlFor(
        'datasets.show', lambda o: {'dataset': o},
        description=_('The dataset page URL'), required=True, fallback_endpoint='api.dataset'),
    'quality': fields.Raw(description=_('The dataset quality'), readonly=True),
    'last_update': fields.ISODateTime(
        description=_('The resources last modification date'), required=True),
}, mask=DEFAULT_MASK)

dataset_page_fields = api.model('DatasetPage', fields.pager(dataset_fields),
                                mask='data{{{0}}},*'.format(DEFAULT_MASK))


dataset_suggestion_fields = api.model('DatasetSuggestion', {
    'id': fields.String(description=_('The dataset identifier')),
    'title': fields.String(description=_('The dataset title')),
    'acronym': fields.String(description=_('An optional dataset acronym')),
    'slug': fields.String(
        description=_('The dataset permalink string')),
    'image_url': fields.String(
        description=_('The dataset (organization) logo URL')),
    'page': fields.UrlFor(
        'datasets.show_redirect', lambda d: {'dataset': d['slug']},
        description=_('The web page URL for this dataset'), fallback_endpoint='api.dataset'),
    'score': fields.Float(description=_('The internal match score')),
})

resource_type_fields = api.model('ResourceType', {
    'id': fields.String(description=_('The resource type identifier')),
    'label': fields.String(description=_('The resource type display name'))
})


schema_fields = api.model('Schema', {
    'id': fields.String(description=_('The schema identifier')),
    'label': fields.String(description=_('The schema display name')),
    'versions': fields.List(fields.String, description=_('The available versions of the schema')),
})
