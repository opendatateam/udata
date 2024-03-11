import json
from datetime import datetime
from io import BytesIO
from uuid import uuid4

import pytest
import pytz
from flask import url_for
import requests_mock

from udata.api import fields
from udata.app import cache
from udata.core import storages
from udata.core.badges.factories import badge_factory
from udata.core.dataset.api_fields import (dataset_harvest_fields,
                                           resource_harvest_fields)
from udata.core.dataset.factories import (CommunityResourceFactory,
                                          DatasetFactory, LicenseFactory,
                                          ResourceFactory, ResourceSchemaMockData,
                                          VisibleDatasetFactory)
from udata.core.dataset.models import (HarvestDatasetMetadata,
                                       HarvestResourceMetadata, ResourceMixin)
from udata.core.organization.factories import OrganizationFactory
from udata.core.spatial.factories import SpatialCoverageFactory
from udata.core.topic.factories import TopicFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.i18n import gettext as _
from udata.models import (LEGACY_FREQUENCIES, RESOURCE_TYPES,
                          UPDATE_FREQUENCIES, CommunityResource, Dataservice,
                          Follow, Member, db)
from udata.tags import MAX_TAG_LENGTH, MIN_TAG_LENGTH
from udata.tests.features.territories import create_geozones_fixtures
from udata.tests.helpers import assert200, assert404, assert204
from udata.utils import faker, unique_string

from . import APITestCase

class DataserviceAPITest(APITestCase):
    modules = []

    def test_dataset_api_create(self):
        self.login()
        response = self.post(url_for('api.dataservices'), {
            'title': 'My API',
            'uri': 'https://example.org',
        })
        self.assert201(response)
        self.assertEqual(Dataservice.objects.count(), 1)

        dataservice = Dataservice.objects.first()

        response = self.get(url_for('api.dataservice', dataservice=dataservice))
        self.assert200(response)

        self.assertEqual(response.json['title'], 'My API')
        self.assertEqual(response.json['uri'], 'https://example.org')

        response = self.patch(url_for('api.dataservice', dataservice=dataservice), {
            'title': 'Updated title',
        })
        self.assert200(response)

        self.assertEqual(response.json['title'], 'Updated title')
        self.assertEqual(response.json['uri'], 'https://example.org')
        dataservice.reload()
        self.assertEqual(dataservice.title, 'Updated title')
        self.assertEqual(dataservice.uri, 'https://example.org')

        response = self.delete(url_for('api.dataservice', dataservice=dataservice))
        self.assert204(response)

        self.assertEqual(Dataservice.objects.count(), 1)

        dataservice.reload()
        self.assertEqual(dataservice.title, 'Updated title')
        self.assertEqual(dataservice.uri, 'https://example.org')
        self.assertIsNotNone(dataservice.deleted)

        # response = self.get(url_for('api.dataservice', dataservice=dataservice))
        # self.assert410(response)

    def test_dataset_api_create_with_validation_error(self):
        self.login()
        response = self.post(url_for('api.dataservices'), {
            'uri': 'https://example.org',
        })
        self.assert400(response)
        self.assertEqual(Dataservice.objects.count(), 0)
