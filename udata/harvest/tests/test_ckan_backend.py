# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging

from datetime import datetime
from os.path import join, dirname, exists
from uuid import uuid4

import httpretty

from udata.models import Dataset, License
from udata.tests import TestCase, DBTestMixin
from udata.core.organization.factories import OrganizationFactory
from udata.utils import faker

from .factories import HarvestSourceFactory
from .. import actions

log = logging.getLogger(__name__)


CKAN_URL = 'http://ckan.test.org/'


def mock_action(action, content):
    if isinstance(content, basestring) and content.endswith('.json'):
        filename = join(dirname(__file__), content)
        with open(filename) as f:
            response = f.read()
    elif callable(content):
        response = content
    else:
        response = json.dumps(content)
    api_url = ''.join((CKAN_URL, 'api/3/action/', action))
    httpretty.register_uri(httpretty.GET, api_url,
                           body=response,
                           content_type='application/json')


def resource_factory():
    return {
        "resource_group_id": str(uuid4()),
        "cache_last_updated": None,
        "revision_timestamp": "2013-10-01T15:59:56.322481",
        "webstore_last_updated": "2013-10-01T17:59:56.238951",
        "id": str(uuid4()),
        "size": "1375",
        "state": "active",
        "hash": "689afc083c6316259955f499580bdf41bfc5e495",
        "description": faker.paragraph(),
        "format": "CSV",
        "tracking_summary": {
            "total": 0,
            "recent": 0
        },
        "mimetype_inner": None,
        "mimetype": "text/csv",
        "cache_url": None,
        "name": faker.sentence(),
        "created": "2013-08-01T09:43:09.031465",
        "url": faker.url(),
        "webstore_url": "active",
        "last_modified": "2013-10-01T17:59:55.552785",
        "position": 0,
        "revision_id": str(uuid4()),
        "resource_type": "file.upload"
    }


def tag_factory(tag):
    timestamp = faker.date_time_between(start_date='-1y', end_date='-1d')
    return {
        "id": str(uuid4()),
        "vocabulary_id": None,
        "display_name": tag,
        "name": tag,
        "revision_timestamp": timestamp.isoformat(),
        "state": "active",
    }


def package_show_factory(name):
    org_id = str(uuid4())
    created = faker.date_time_between(start_date='-3y', end_date='-7d')
    updated = faker.date_time_between(start_date='-7d', end_date='now')
    nb_resources = faker.randomize_nb_elements(4)
    nb_tags = faker.randomize_nb_elements(10)
    return {
        "help": "",
        "success": True,
        "result": {
            "license_title": "Licence ouverte / Open license (Etalab)",
            "maintainer": None,
            "relationships_as_object": [],
            "private": False,
            "maintainer_email": None,
            "revision_timestamp": updated.isoformat(),
            "id": str(uuid4()),
            "metadata_created": created.isoformat(),
            "owner_org": org_id,
            "metadata_modified": updated.isoformat(),
            "author": None,
            "author_email": None,
            "state": "active",
            "version": None,
            "license_id": "lool",
            "type": "dataset",
            "resources": [resource_factory()
                          for _ in range(nb_resources)],
            "num_resources": nb_resources,
            "tags": [tag_factory(faker.word())
                     for _ in range(nb_tags)],
            "tracking_summary": {
                "total": 0,
                "recent": 0
            },
            "groups": [{
                "title": " Actions Région",
                "description": "Les actions régionales, l'agriculture, l'aménagement du territoire...",  # noqa
                "name": "actions-region",
                "id": "7859d498-316e-4a31-8487-f7f26df0929e"
            }],
            "relationships_as_subject": [],
            "num_tags": nb_tags,
            "name": faker.slug(),
            "isopen": False,
            "url": None,
            "notes": faker.paragraph(),
            "title": faker.sentence(),
            "extras": [{
                "value": "01/08/2013",
                "key": "date",
                "__extras": {
                    "package_id": "f9f07d12-f810-4cb5-b3c0-52d7b1130c2e",
                    "revision_id": "e108a7c6-0e5f-4714-a8e6-68162c69ae68"
                }
            }, {
                "value": "Annuelle",
                "key": "freqMAJ",
                "__extras": {
                    "revision_id": "e108a7c6-0e5f-4714-a8e6-68162c69ae68",
                    "package_id": "f9f07d12-f810-4cb5-b3c0-52d7b1130c2e"
                }
            }],
            "license_url": "http://www.etalab.gouv.fr/pages/Licence_ouverte_Open_licence-5899923.html",  # noqa
            "organization": {
                "description": "",
                "created": "2013-07-18T11:25:15.969631",
                "title": "Conseil Régional Nord-Pas de Calais",
                "name": "conseil-regional-nord-pas-de-calais",
                "revision_timestamp": "2013-07-29T15:25:28.634142",
                "is_organization": True,
                "state": "active",
                "image_url": "/images/npdc-icon.png",
                "revision_id": str(uuid4()),
                "type": "organization",
                "id": org_id,
                "approval_status": "approved"
            },
            "revision_id": str(uuid4())
        }
    }


class CkanBackendTest(DBTestMixin, TestCase):
    def setUp(self):
        # Create fake licenses
        for license_id in 'lool', 'fr-lo':
            License.objects.create(id=license_id, title=license_id)

    @httpretty.activate
    def test_simple(self):
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='ckan',
                                      url=CKAN_URL,
                                      organization=org)

        mock_action('package_list', {
            'success': True,
            'result': [
                'dataset-1',
                'dataset-2',
                'dataset-3',
            ]
        })

        def package_show_responses(request, uri, headers):
            dataset_id = request.querystring['id'][0]
            filename = 'ckan-{0}.json'.format(dataset_id)
            filename = join(dirname(__file__), filename)
            if not exists(filename):
                msg = 'Requested an unexpected dataset: {0}'.format(dataset_id)
                self.fail(msg)
            with open(filename) as f:
                response = f.read()
            return 200, headers, response

        mock_action('package_show', package_show_responses)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        self.assertEqual(len(job.items), 3)

        datasets = {d.extras['ckan:name']: d for d in Dataset.objects}
        self.assertEqual(len(datasets), 2)

        self.assertIn('dataset-1', datasets)
        d = datasets['dataset-1']
        self.assertEqual(d.title, 'Dataset 1')
        self.assertEqual(d.description, "Description 1")
        self.assertEqual(d.tags, ['country-uk',
                                  'date-2009',
                                  'openspending',
                                  'regional'])
        self.assertEqual(d.extras['harvest:remote_id'],
                         '7e4d4ef3-f452-4c35-963d-9c6e582374b3')
        self.assertEqual(d.extras['harvest:domain'], 'ckan.test.org')
        self.assertEqual(d.extras['ckan:name'], 'dataset-1')
        # self.assertEqual(d.license.id, "fr-lo")

        self.assertEqual(len(d.resources), 3)
        resource = d.resources[0]
        self.assertEqual(resource.title, 'Resource 1')
        self.assertEqual(resource.description, 'Resource description 1')
        self.assertEqual(resource.format, 'csv')
        self.assertEqual(resource.mime, 'text/csv')
        self.assertIsInstance(resource.modified, datetime)
        self.assertEqual(resource.url,
                         ('http://ckan.net/storage/f/file/'
                          '3ffdcd42-5c63-4089-84dd-c23876259973'))

        # dataset-2 has geo feature
        self.assertIn('dataset-2', datasets)
        d = datasets['dataset-2']
        self.assertEqual(
            d.tags,
            ['africa',
             # 'b' must be absent,
             'b' * 32,  # 'b' * 33 must be truncated
             'cables-cables',  # the tag must be slugified
             'fibre',
             'optic',
             'terrestrial'])
        self.assertEqual(len(d.resources), 1)
        self.assertEqual(d.spatial.geom['coordinates'],
                         [[[[50.8, -34.2],
                            [50.8, 36.7],
                            [-19.9, 36.7],
                            [-19.9, -34.2],
                            [50.8, -34.2]]]])

        # dataset-3 has no data
        self.assertNotIn('dataset-3', datasets)
