from flask import url_for

from udata.api import api, API
from udata.forms import Form, fields

from . import APITestCase

ns = api.namespace('fake-ns', 'A Fake namespace')


@ns.route('/options', endpoint='fake-options')
class FakeAPI(API):
    def get(self):
        return {'success': True}


@ns.route('/fake-form', endpoint='fake-form')
class FakeFormAPI(API):
    def post(self):
        class FakeForm(Form):
            pass
        api.validate(FakeForm)
        return {'success': True}


class OptionsCORSTest(APITestCase):
    def test_should_allow_options_and_cors(self):
        '''Should allow OPTIONS operation and give cors parameters'''
        response = self.client.options(url_for('api.fake-options'))

        self.assert200(response)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], '*')
        allowed_methods = response.headers['Allow']
        self.assertIn('HEAD', allowed_methods)
        self.assertIn('OPTIONS', allowed_methods)
        self.assertIn('GET', allowed_methods)

        response = self.client.options(
            url_for('api.fake-options'),
            headers={
                'Access-Control-Request-Method': 'GET',
                'Authorization': 'Bearer YouWillNeverGuess',
                'Access-Control-Request-Headers': 'Authorization'
            }
        )
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], '*')
        self.assertEqual(response.headers['Access-Control-Allow-Headers'], 'Authorization')
        self.assertEqual(
            response.headers['Access-Control-Allow-Methods'],
            'DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT'
            )


class JSONFormRequestTest(APITestCase):
    def test_non_json_content_type(self):
        '''We expect JSON requests for forms and enforce it'''
        response = self.client.post(url_for('api.fake-form'), {}, headers={
            'Content-Type': 'multipart/form-data'
        })
        self.assert400(response)
        self.assertEqual(
            response.json,
            {'errors': {'Content-Type': 'expecting application/json'}}
        )

    def test_json_content_type(self):
        '''We expect JSON requests for forms and enforce it'''
        response = self.post(url_for('api.fake-form'), {})
        self.assert200(response)
