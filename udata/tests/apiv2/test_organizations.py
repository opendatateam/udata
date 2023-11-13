from flask import url_for

from udata.tests.api import APITestCase

from udata.core.organization.factories import OrganizationFactory, Member


class OrganizationExtrasAPITest(APITestCase):
    modules = None

    def setUp(self):
        self.login()
        member = Member(user=self.user, role='admin')
        self.org = OrganizationFactory(members=[member])

    def test_get_organization_extras(self):
        self.org.extras = {'test::extra': 'test-value'}
        self.org.save()
        response = self.get(url_for('apiv2.organization_extras', org=self.org))
        self.assert200(response)
        data = response.json
        assert data['test::extra'] == 'test-value'

    def test_update_organization_extras(self):
        self.org.extras = {
            'test::extra': 'test-value',
            'test::extra-second': 'test-value-second',
            'test::none-will-be-deleted': 'test-value',
        }
        self.org.save()

        data = ['test::extra-second', 'another::key']
        response = self.put(url_for('apiv2.organization_extras', org=self.org), data)
        self.assert400(response)
        assert response.json['message'] == 'Wrong payload format, dict expected'

        data = {
            'test::extra-second': 'test-value-changed',
            'another::key': 'another-value',
            'test::none': None,
            'test::none-will-be-deleted': None,
        }
        response = self.put(url_for('apiv2.organization_extras', org=self.org), data)
        self.assert200(response)

        self.org.reload()
        assert self.org.extras['test::extra'] == 'test-value'
        assert self.org.extras['test::extra-second'] == 'test-value-changed'
        assert self.org.extras['another::key'] == 'another-value'
        assert 'test::none' not in self.org.extras
        assert 'test::none-will-be-deleted' not in self.org.extras

    def test_delete_organization_extras(self):
        self.org.extras = {'test::extra': 'test-value', 'another::key': 'another-value'}
        self.org.save()

        data = {'another::key': 'another-value'}
        response = self.delete(url_for('apiv2.organization_extras', org=self.org), data)
        self.assert400(response)
        assert response.json['message'] == 'Wrong payload format, list expected'

        data = ['another::key']
        response = self.delete(url_for('apiv2.organization_extras', org=self.org), data)
        self.assert204(response)

        self.org.reload()
        assert len(self.org.extras) == 1
        assert self.org.extras['test::extra'] == 'test-value'

    def test_update_organization_custom_extras(self):
        data = {
            "custom": [
                {
                    "title": "color",
                    "description": "the banner color of the dataset (Hex code)",
                    "type": "tuple"
                }
            ]
        }
        response = self.put(url_for('apiv2.organization_extras', org=self.org), data)
        self.assert400(response)

        data = {
            "custom": [
                {
                    "title": "color",
                    "description": "the banner color of the dataset (Hex code)",
                    "type": "str"
                }
            ]
        }
        response = self.put(url_for('apiv2.organization_extras', org=self.org), data)
        self.assert200(response)
        self.org.reload()
        assert self.org.extras['custom'][0]['title'] == 'color'
        assert self.org.extras['custom'][0]['description'] == 'the banner color of the dataset (Hex code)'
        assert self.org.extras['custom'][0]['type'] == 'str'
