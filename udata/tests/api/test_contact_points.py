import pytest

from flask import url_for

from udata.models import ContactPoint
from udata.core.contact_points.factories import ContactPointFactory

from udata.tests.helpers import assert200, assert204

pytestmark = [
    pytest.mark.usefixtures('clean_db'),
]


class ContactPointAPITest:
    modules = []

    def test_contact_points_api_list(self, api):
        contact_points = ContactPointFactory.create_batch(3)

        response = api.get(url_for('api.contact_points'))
        assert200(response)
        len(response.json['data']) == len(contact_points)

    def test_contact_point_api_update(self, api):
        user = api.login()
        contact_point = ContactPointFactory()
        data = contact_point.to_dict()
        data['email'] = 'new.email@newdomain.com'
        response = api.put(url_for('api.contact_point', contact_point=contact_point), data)
        assert200(response)
        assert ContactPoint.objects.count() is 1
        assert ContactPoint.objects.first().email == 'new.email@newdomain.com'

    def test_contact_point_api_delete(self, api):
        user = api.login()
        contact_point = ContactPointFactory()
        response = api.delete(url_for('api.contact_point', contact_point=contact_point))
        assert204(response)
        assert ContactPoint.objects.count() is 0