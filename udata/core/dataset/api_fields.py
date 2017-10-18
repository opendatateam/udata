# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.api import api, fields, base_reference
from udata.core.badges.api import badge_fields
from udata.core.organization.api_fields import org_ref_fields
from udata.core.spatial.api_fields import spatial_coverage_fields
from udata.core.user.api_fields import user_ref_fields

from .models import (
    UPDATE_FREQUENCIES, RESOURCE_TYPES, DEFAULT_FREQUENCY,
    CHECKSUM_TYPES, DEFAULT_CHECKSUM_TYPE, DEFAULT_LICENSE
)

checksum_fields = api.model('Checksum', {
    'type': fields.String(
        description='The hashing algorithm used to compute the checksum',
        default=DEFAULT_CHECKSUM_TYPE, enum=CHECKSUM_TYPES),
    'value': fields.String(description="The resulting checksum/hash",
                           required=True)
})

license_fields = api.model('License', {
    'id': fields.String(description='The license identifier', required=True),
    'title': fields.String(description='The resource title', required=True),
    'maintainer': fields.String(description='The license official maintainer'),
    'url': fields.String(description='The license official URL'),
    'flags': fields.List(fields.String, description='Some arbitry flags'),
})

frequency_fields = api.model('Frequency', {
    'id': fields.String(description='The frequency identifier'),
    'label': fields.String(description='The frequency display name')
})

resource_fields = api.model('Resource', {
    'id': fields.String(description='The resource unique ID', readonly=True),
    'title': fields.String(description='The resource title', required=True),
    'description': fields.Markdown(
        description='The resource markdown description'),
    'filetype': fields.String(
        description=('Whether the resource is an uploaded file, '
                     'a remote file or an API'),
        required=True, enum=RESOURCE_TYPES.keys()),
    'format': fields.String(description='The resource format', required=True),
    'url': fields.String(description='The resource URL', required=True),
    'latest': fields.String(description='The permanent URL redirecting to '
                            'the latest version of the resource. When the '
                            'resource data is updated, the URL will '
                            'change, the latest URL won\'t.',
                            readonly=True),
    'checksum': fields.Nested(
        checksum_fields, allow_null=True,
        description='A checksum to validate file validity'),
    'filesize': fields.Integer(description='The resource file size in bytes'),
    'mime': fields.String(description='The resource mime type'),
    'created_at': fields.ISODateTime(
        readonly=True, description='The resource creation date'),
    'published': fields.ISODateTime(
        description='The resource publication date'),
    'last_modified': fields.ISODateTime(
        attribute='modified', readonly=True,
        description='The resource last modification date'),
    'metrics': fields.Raw(description='The resource metrics', readonly=True),
    'extras': fields.Raw(description='Extra attributes as key-value pairs'),
})

upload_fields = api.inherit('UploadedResource', resource_fields, {
    'success': fields.Boolean(
        description='Whether the upload succeeded or not.',
        readonly=True, default=True),
})

resources_order = api.as_list(fields.String(description='Resource ID'))

temporal_coverage_fields = api.model('TemporalCoverage', {
    'start': fields.ISODateTime(description='The temporal coverage start date',
                                required=True),
    'end': fields.ISODateTime(description='The temporal coverage end date',
                              required=True),
})

dataset_ref_fields = api.inherit('DatasetReference', base_reference, {
    'title': fields.String(description='The dataset title', readonly=True),
    'uri': fields.UrlFor(
        'api.dataset', lambda d: {'dataset': d},
        description='The API URI for this dataset', readonly=True),
    'page': fields.UrlFor(
        'datasets.show', lambda d: {'dataset': d},
        description='The web page URL for this dataset', readonly=True),
})

community_resource_fields = api.inherit('CommunityResource', resource_fields, {
    'dataset': fields.Nested(
        dataset_ref_fields, allow_null=True,
        description='Reference to the associated dataset'),
    'organization': fields.Nested(
        org_ref_fields, allow_null=True,
        description='The producer organization'),
    'owner': fields.Nested(
        user_ref_fields, allow_null=True,
        description='The user information')
})

community_resource_page_fields = api.model(
    'CommunityResourcePage', fields.pager(community_resource_fields))

#: Default mask to make it lightweight by default
DEFAULT_MASK = ','.join((
    'id', 'title', 'slug', 'description', 'created_at', 'last_modified', 'deleted',
    'private', 'tags', 'badges', 'resources', 'frequency', 'frequency_date', 'extras',
    'metrics', 'organization', 'owner', 'temporal_coverage', 'spatial', 'license',
    'uri', 'page', 'last_update'
))

dataset_fields = api.model('Dataset', {
    'id': fields.String(description='The dataset identifier', readonly=True),
    'title': fields.String(description='The dataset title', required=True),
    'slug': fields.String(
        description='The dataset permalink string', required=True),
    'description': fields.Markdown(
        description='The dataset description in markdown', required=True),
    'created_at': fields.ISODateTime(
        description='The dataset creation date', required=True),
    'last_modified': fields.ISODateTime(
        description='The dataset last modification date', required=True),
    'deleted': fields.ISODateTime(description='The deletion date if deleted'),
    'featured': fields.Boolean(description='Is the dataset featured'),
    'private': fields.Boolean(
        description='Is the dataset private to the owner or the organization'),
    'tags': fields.List(fields.String),
    'badges': fields.List(fields.Nested(badge_fields),
                          description='The dataset badges',
                          readonly=True),
    'resources': fields.List(
        fields.Nested(resource_fields, description='The dataset resources')),
    'community_resources': fields.List(
        fields.Nested(
            community_resource_fields,
            description='The dataset community submitted resources')),
    'frequency': fields.String(
        description='The update frequency', required=True,
        enum=UPDATE_FREQUENCIES.keys(), default=DEFAULT_FREQUENCY),
    'frequency_date': fields.ISODateTime(
        description=('Next expected update date, you will be notified '
                     'once that date is reached.')),
    'extras': fields.Raw(description='Extras attributes as key-value pairs'),
    'metrics': fields.Raw(description='The dataset metrics'),
    'organization': fields.Nested(
        org_ref_fields, allow_null=True,
        description='The producer organization'),
    'owner': fields.Nested(
        user_ref_fields, allow_null=True, description='The user information'),
    'temporal_coverage': fields.Nested(
        temporal_coverage_fields, allow_null=True,
        description='The temporal coverage'),
    'spatial': fields.Nested(
        spatial_coverage_fields, allow_null=True,
        description='The spatial coverage'),
    'license': fields.String(attribute='license.id',
                             default=DEFAULT_LICENSE['id'],
                             description='The dataset license'),
    'uri': fields.UrlFor(
        'api.dataset', lambda o: {'dataset': o},
        description='The dataset API URI', required=True),
    'page': fields.UrlFor(
        'datasets.show', lambda o: {'dataset': o},
        description='The dataset page URL', required=True),
    'quality': fields.Raw(description='The dataset quality', readonly=True),
    'last_update': fields.ISODateTime(
        description='The resources last modification date', required=True),
}, mask=DEFAULT_MASK)

dataset_page_fields = api.model('DatasetPage', fields.pager(dataset_fields),
                                mask='data{{{0}}},*'.format(DEFAULT_MASK))


dataset_suggestion_fields = api.model('DatasetSuggestion', {
    'id': fields.String(description='The dataset identifier', required=True),
    'title': fields.String(description='The dataset title', required=True),
    'slug': fields.String(
        description='The dataset permalink string', required=True),
    'image_url': fields.String(
        description='The dataset (organization) logo URL'),
    'page': fields.UrlFor(
        'datasets.show_redirect', lambda d: {'dataset': d['slug']},
        description='The web page URL for this dataset', readonly=True),
    'score': fields.Float(
        description='The internal match score', required=True),
})
