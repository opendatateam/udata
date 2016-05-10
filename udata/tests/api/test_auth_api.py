# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import skip

from flask import url_for


from udata.auth import PermissionDenied
from udata.api import api, API
from udata.api.oauth2 import OAuth2Client, OAuth2Token
from udata.forms import Form, fields, validators

from . import APITestCase
from udata.core.user.factories import UserFactory

ns = api.namespace('fake', 'A Fake namespace')


class FakeForm(Form):
    required = fields.StringField(validators=[validators.required()])
    choices = fields.SelectField(choices=(('first', ''), ('second', '')))
    email = fields.StringField(validators=[validators.Email()])


@ns.route('/', endpoint='fake')
class FakeAPI(API):
    @api.secure
    def post(self):
        return {'success': True}

    def get(self):
        return {'success': True}

    def put(self):
        api.validate(FakeForm)
        return {'success': True}


class APIAuthTest(APITestCase):
    def oauth_app(self, name='test-client'):
        owner = UserFactory()
        return OAuth2Client.objects.create(
            name=name,
            owner=owner,
            redirect_uris=['https://test.org/callback']
        )

    def test_no_auth(self):
        '''Should not return a content type if there is no content on delete'''
        response = self.get(url_for('api.fake'))

        self.assert200(response)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json, {'success': True})

    def test_session_auth(self):
        '''Should handle session authentication'''
        self.login()

        response = self.post(url_for('api.fake'))

        self.assert200(response)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json, {'success': True})

    def test_header_auth(self):
        '''Should handle header API Key authentication'''
        user = UserFactory(apikey='apikey')
        response = self.post(url_for('api.fake'),
                             headers={'X-API-KEY': user.apikey})

        self.assert200(response)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json, {'success': True})

    def test_oauth_auth(self):
        '''Should handle  OAuth header authentication'''
        user = UserFactory()
        client = self.oauth_app()
        token = OAuth2Token.objects.create(
            client=client,
            user=user,
            access_token='access-token',
            refresh_token='refresh-token'
        )

        response = self.post(url_for('api.fake'), headers={
            'Authorization': ' '.join(['Bearer', token.access_token])
        })

        self.assert200(response)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json, {'success': True})

    def test_no_apikey(self):
        '''Should raise a HTTP 401 if no API Key is provided'''
        response = self.post(url_for('api.fake'))

        self.assert401(response)
        self.assertEqual(response.content_type, 'application/json')
        self.assertIn('message', response.json)

    def test_invalid_apikey(self):
        '''Should raise a HTTP 401 if an invalid API Key is provided'''
        response = self.post(url_for('api.fake'),
                             headers={'X-API-KEY': 'fake'})

        self.assert401(response)
        self.assertEqual(response.content_type, 'application/json')
        self.assertIn('message', response.json)

    def test_inactive_user(self):
        '''Should raise a HTTP 401 if the user is inactive'''
        user = UserFactory(apikey='apikey', active=False)
        response = self.post(url_for('api.fake'),
                             headers={'X-API-KEY': user.apikey})

        self.assert401(response)
        self.assertEqual(response.content_type, 'application/json')
        self.assertIn('message', response.json)

    def test_validation_errors(self):
        '''Should raise a HTTP 400 and returns errors on validation error'''
        response = self.put(url_for('api.fake'), {'email': 'wrong'})

        self.assert400(response)
        self.assertEqual(response.content_type, 'application/json')

        for field in 'required', 'email', 'choices':
            self.assertIn(field, response.json['errors'])
            self.assertIsInstance(response.json['errors'][field], list)

    def test_no_validation_error(self):
        '''Should pass if no validation error'''
        response = self.put(url_for('api.fake'), {
            'required': 'value',
            'email': 'coucou@cmoi.fr',
            'choices': 'first',
        })

        self.assert200(response)
        self.assertEqual(response.json, {'success': True})

    def test_authorization_display(self):
        '''Should display the OAuth authorization page'''
        self.login()

        client = self.oauth_app()
        response = self.get(url_for(
            'oauth-i18n.authorize',
            response_type='code',
            client_id=client.client_id,
            redirect_uri=client.default_redirect_uri
        ))

        self.assert200(response)

    def test_authorization_decline(self):
        '''Should redirect to the redirect_uri on authorization denied'''
        self.login()

        client = self.oauth_app()
        response = self.post(url_for(
            'oauth-i18n.authorize',
            response_type='code',
            client_id=client.client_id,
            redirect_uri=client.default_redirect_uri
        ), {
            'scopes': ['default'],
            'refuse': '',
        })

        self.assertStatus(response, 302)
        uri, params = response.location.split('?')
        self.assertEqual(uri, client.default_redirect_uri)

    def test_authorization_accept(self):
        '''Should redirect to the redirect_uri on authorization accepted'''
        self.login()

        client = self.oauth_app()

        response = self.post(url_for(
            'oauth-i18n.authorize',
            response_type='code',
            client_id=client.client_id,
            redirect_uri=client.default_redirect_uri
        ), {
            'scopes': ['default'],
            'accept': '',
        })

        self.assertStatus(response, 302)
        uri, params = response.location.split('?')
        self.assertEqual(uri, client.default_redirect_uri)

    def test_value_error(self):
        @ns.route('/exception', endpoint='exception')
        class ExceptionAPI(API):
            def get(self):
                raise ValueError('Not working')

        response = self.get(url_for('api.exception'))

        self.assert400(response)
        self.assertEqual(response.json['message'], 'Not working')

    @skip('Need flask-restplus handling')
    def test_permission_denied(self):
        @ns.route('/exception', endpoint='exception')
        class ExceptionAPI(API):
            def get(self):
                raise PermissionDenied('Permission denied')

        response = self.get(url_for('api.exception'))

        self.assert403(response)
        self.assertIn('message', response.json)
