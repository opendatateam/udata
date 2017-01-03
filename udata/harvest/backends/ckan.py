# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging

from uuid import UUID
from urlparse import urljoin

from voluptuous import (
    Schema, All, Any, Lower, Coerce, DefaultTo
)


from udata.models import db, Resource, License, SpatialCoverage
from udata.utils import get_by, daterange_start, daterange_end

from . import BaseBackend, register
from ..exceptions import HarvestException, HarvestSkipException
from ..filters import (
    boolean, email, to_date, slug, normalize_tag, normalize_string,
    is_url, empty_none, hash
)

log = logging.getLogger(__name__)

RESOURCE_TYPES = ('file', 'file.upload', 'api', 'documentation',
                  'image', 'visualization')

ALLOWED_RESOURCE_TYPES = ('file', 'file.upload', 'api')

resource = {
    'id': basestring,
    'position': int,
    'name': All(DefaultTo(''), basestring),
    'description': All(basestring, normalize_string),
    'format': All(basestring, Lower),
    'mimetype': Any(All(basestring, Lower), None),
    'size': Any(Coerce(int), None),
    'hash': Any(All(basestring, hash), None),
    'created': All(basestring, to_date),
    'last_modified': Any(All(basestring, to_date), None),
    'url': All(basestring, is_url(full=True)),
    'resource_type': All(empty_none,
                         DefaultTo('file'),
                         basestring,
                         Any(*RESOURCE_TYPES)
                         ),
}

tag = {
    'id': basestring,
    'vocabulary_id': Any(basestring, None),
    'display_name': basestring,
    'name': All(basestring, normalize_tag),
    'state': basestring,
}

organization = {
    'id': basestring,
    'description': basestring,
    'created': All(basestring, to_date),
    'title': basestring,
    'name': All(basestring, slug),
    'revision_timestamp': All(basestring, to_date),
    'is_organization': boolean,
    'state': basestring,
    'image_url': basestring,
    'revision_id': basestring,
    'type': 'organization',
    'approval_status': 'approved'
}

schema = Schema({
    'id': basestring,
    'name': basestring,
    'title': basestring,
    'notes': All(basestring, normalize_string),
    'license_id': All(DefaultTo('not-specified'), basestring),
    'tags': [tag],

    'metadata_created': All(basestring, to_date),
    'metadata_modified': All(basestring, to_date),
    'organization': Any(organization, None),
    'resources': [resource],
    'revision_id': basestring,
    'extras': [{
        'key': basestring,
        'value': Any(basestring, int, float, boolean, {}, []),
    }],
    'private': boolean,
    'type': 'dataset',
    'author': Any(basestring, None),
    'author_email': All(empty_none, Any(All(basestring, email), None)),
    'maintainer': Any(basestring, None),
    'maintainer_email': All(empty_none, Any(All(basestring, email), None)),
    'state': Any(basestring, None),
}, required=True, extra=True)


@register
class CkanBackend(BaseBackend):
    name = 'ckan'
    display_name = 'CKAN'

    def get_headers(self):
        headers = super(CkanBackend, self).get_headers()
        headers['content-type'] = 'application/json'
        if self.config.get('apikey'):
            headers['Authorization'] = self.config['apikey']
        return headers

    def action_url(self, endpoint):
        path = '/'.join(['api/3/action', endpoint])
        return urljoin(self.source.url, path)

    def get_action(self, endpoint, fix=False, **kwargs):
        url = self.action_url(endpoint)
        if fix:
            response = self.post(url, '{}', params=kwargs)
        else:
            response = self.get(url, params=kwargs)
        if response.status_code != 200:
            msg = response.text.strip('"')
            raise HarvestException(msg)
        return response.json()

    def get_status(self):
        url = urljoin(self.source.url, '/api/util/status')
        response = self.get(url)
        return response.json()

    def initialize(self):
        '''List all datasets for a given ...'''
        # status = self.get_status()
        # fix = status['ckan_version'] < '1.8'
        fix = False
        response = self.get_action('package_list', fix=fix)
        names = response['result']
        if self.max_items:
            names = names[:self.max_items]
        for name in names:
            self.add_item(name)

    def process(self, item):
        response = self.get_action('package_show', id=item.remote_id)
        data = self.validate(response['result'], schema)

        # Fix the remote_id: use real ID instead of not stable name
        item.remote_id = data['id']

        # Skip if no resource
        if not len(data.get('resources', [])):
            msg = 'Dataset {0} has no record'.format(item.remote_id)
            raise HarvestSkipException(msg)

        dataset = self.get_dataset(item.remote_id)

        # Core attributes
        if not dataset.slug:
            dataset.slug = data['name']
        dataset.title = data['title']
        dataset.description = data['notes']
        dataset.license = License.objects(id=data['license_id']).first()
        # dataset.license = license or License.objects.get(id='notspecified')
        dataset.tags = [t['name'] for t in data['tags'] if t['name']]

        dataset.created_at = data['metadata_created']
        dataset.last_modified = data['metadata_modified']

        dataset.extras['ckan:name'] = data['name']

        temporal_start, temporal_end = None, None
        spatial_geom = None

        for extra in data['extras']:
            # GeoJSON representation (Polygon or Point)
            if extra['key'] == 'spatial':
                spatial_geom = json.loads(extra['value'])
            #  Textual representation of the extent / location
            elif extra['key'] == 'spatial-text':
                log.debug('spatial-text value not handled')
                print 'spatial-text', extra['value']
            # Linked Data URI representing the place name
            elif extra['key'] == 'spatial-uri':
                log.debug('spatial-uri value not handled')
                print 'spatial-uri', extra['value']
            # Update frequency
            elif extra['key'] == 'frequency':
                print 'frequency', extra['value']
            # Temporal coverage start
            elif extra['key'] == 'temporal_start':
                print 'temporal_start', extra['value']
                temporal_start = daterange_start(extra['value'])
                continue
            # Temporal coverage end
            elif extra['key'] == 'temporal_end':
                print 'temporal_end', extra['value']
                temporal_end = daterange_end(extra['value'])
                continue
            # else:
            #     print extra['key'], extra['value']
            dataset.extras[extra['key']] = extra['value']

        if spatial_geom:
            dataset.spatial = SpatialCoverage()
            if spatial_geom['type'] == 'Polygon':
                coordinates = [spatial_geom['coordinates']]
            elif spatial_geom['type'] == 'MultiPolygon':
                coordinates = spatial_geom['coordinates']
            else:
                HarvestException('Unsupported spatial geometry')
            dataset.spatial.geom = {
                'type': 'MultiPolygon',
                'coordinates': coordinates
            }

        if temporal_start and temporal_end:
            dataset.temporal_coverage = db.DateRange(
                start=temporal_start,
                end=temporal_end,
            )

        # Remote URL
        if data.get('url'):
            dataset.extras['remote_url'] = data['url']

        # Resources
        for res in data['resources']:
            if res['resource_type'] not in ALLOWED_RESOURCE_TYPES:
                continue
            try:
                resource = get_by(dataset.resources, 'id', UUID(res['id']))
            except:
                log.error('Unable to parse resource ID %s', res['id'])
                continue
            if not resource:
                resource = Resource(id=res['id'])
                dataset.resources.append(resource)
            resource.title = res.get('name', '') or ''
            resource.description = res.get('description')
            resource.url = res['url']
            resource.filetype = ('api' if res['resource_type'] == 'api'
                                 else 'remote')
            resource.format = res.get('format')
            resource.mime = res.get('mimetype')
            resource.hash = res.get('hash')
            resource.created = res['created']
            resource.modified = res['last_modified']
            resource.published = resource.published or resource.created

        return dataset
