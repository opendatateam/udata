import pytest

from base64 import b64encode
from urllib.parse import parse_qs

from flask import url_for
from authlib.common.security import generate_token
from authlib.common.urls import urlparse, url_decode
from authlib.oauth2.rfc7636 import (
    CodeChallenge as _CodeChallenge,
    create_s256_code_challenge,
)

from udata.api import api, API
from udata.api.oauth2 import OAuth2Client, OAuth2Token
from udata.auth import PermissionDenied
from udata.core.user.factories import UserFactory
from udata.forms import Form, fields, validators
from udata.tests.helpers import (
    assert200, assert400, assert401, assert403, assert_status
)

ns = api.namespace('fake', 'A Fake namespace')


class FakeForm(Form):
    required = fields.StringField(validators=[validators.DataRequired()])
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


def basic_header(client):
    payload = ':'.join((client.client_id, client.secret))
    token = b64encode(payload.encode('utf-8')).decode('utf8')
    return {'Authorization': 'Basic {}'.format(token)}


@pytest.fixture
def oauth(app, request):
    marker = request.node.get_closest_marker('oauth')
    kwargs = marker.kwargs if marker else {}
    return OAuth2Client.objects.create(
        name='test-client',
        owner=UserFactory(),
        redirect_uris=['https://test.org/callback'],
        **kwargs
    )


@pytest.mark.usefixtures('clean_db')
class APIAuthTest:
    modules = []

    def test_no_auth(self, api):
        '''Should not return a content type if there is no content on delete'''
        response = api.get(url_for('api.fake'))

        assert200(response)
        assert response.content_type == 'application/json'
        assert response.json == {'success': True}

    def test_session_auth(self, api):
        '''Should handle session authentication'''
        api.client.login()  # Session auth

        response = api.post(url_for('api.fake'))

        assert200(response)
        assert response.content_type == 'application/json'
        assert response.json == {'success': True}

    def test_header_auth(self, api):
        '''Should handle header API Key authentication'''
        with api.user() as user:  # API Key auth
            response = api.post(url_for('api.fake'),
                                headers={'X-API-KEY': user.apikey})

        assert200(response)
        assert response.content_type == 'application/json'
        assert response.json == {'success': True}

    def test_oauth_auth(self, api, oauth):
        '''Should handle OAuth header authentication'''
        user = UserFactory()
        token = OAuth2Token.objects.create(
            client=oauth,
            user=user,
            access_token='access-token',
            refresh_token='refresh-token',
        )

        response = api.post(url_for('api.fake'), headers={
            'Authorization': ' '.join(['Bearer', token.access_token])
        })

        assert200(response)
        assert response.content_type == 'application/json'
        assert response.json == {'success': True}

    def test_bad_oauth_auth(self, api, oauth):
        '''Should handle wrong OAuth header authentication'''
        user = UserFactory()
        OAuth2Token.objects.create(
            client=oauth,
            user=user,
            access_token='access-token',
            refresh_token='refresh-token',
        )

        response = api.post(url_for('api.fake'), headers={
            'Authorization': ' '.join(['Bearer', 'not-my-token'])
        })

        assert401(response)
        assert response.content_type == 'application/json'

    def test_no_apikey(self, api):
        '''Should raise a HTTP 401 if no API Key is provided'''
        response = api.post(url_for('api.fake'))

        assert401(response)
        assert response.content_type == 'application/json'
        assert 'message' in response.json

    def test_invalid_apikey(self, api):
        '''Should raise a HTTP 401 if an invalid API Key is provided'''
        response = api.post(url_for('api.fake'), headers={'X-API-KEY': 'fake'})

        assert401(response)
        assert response.content_type == 'application/json'
        assert 'message' in response.json

    def test_inactive_user(self, api):
        '''Should raise a HTTP 401 if the user is inactive'''
        user = UserFactory(active=False)
        with api.user(user) as user:
            response = api.post(url_for('api.fake'),
                                headers={'X-API-KEY': user.apikey})

        assert401(response)
        assert response.content_type == 'application/json'
        assert 'message' in response.json
    
    def test_deleted_user(self, api):
        '''Should raise a HTTP 401 if the user is deleted'''
        user = UserFactory()
        user.mark_as_deleted()
        with api.user(user) as user:
            response = api.post(url_for('api.fake'),
                                headers={'X-API-KEY': user.apikey})

        assert401(response)
        assert response.content_type == 'application/json'
        assert 'message' in response.json

    def test_validation_errors(self, api):
        '''Should raise a HTTP 400 and returns errors on validation error'''
        response = api.put(url_for('api.fake'), {'email': 'wrong'})

        assert400(response)
        assert response.content_type == 'application/json'

        for field in 'required', 'email', 'choices':
            assert field in response.json['errors']
            assert isinstance(response.json['errors'][field], list)

    def test_no_validation_error(self, api):
        '''Should pass if no validation error'''
        response = api.put(url_for('api.fake'), {
            'required': 'value',
            'email': 'coucou@cmoi.fr',
            'choices': 'first',
        })

        assert200(response)
        assert response.json == {'success': True}

    def test_authorization_display(self, client, oauth):
        '''Should display the OAuth authorization page'''
        client.login()

        response = client.get(url_for(
            'oauth.authorize',
            response_type='code',
            client_id=oauth.client_id,
            redirect_uri=oauth.default_redirect_uri
        ))

        assert200(response)

    def test_authorization_decline(self, client, oauth):
        '''Should redirect to the redirect_uri on authorization denied'''
        client.login()

        response = client.post(url_for(
            'oauth.authorize',
            response_type='code',
            client_id=oauth.client_id,
            redirect_uri=oauth.default_redirect_uri
        ), {
            'scope': 'default',
            'refuse': '',
        })

        assert_status(response, 302)
        uri, params = response.location.split('?')
        assert uri == oauth.default_redirect_uri

    def test_authorization_accept(self, client, oauth):
        '''Should redirect to the redirect_uri on authorization accepted'''
        client.login()

        response = client.post(url_for(
            'oauth.authorize',
            response_type='code',
            client_id=oauth.client_id,
            redirect_uri=oauth.default_redirect_uri
        ), {
            'scope': 'default',
            'accept': '',
        })

        assert_status(response, 302)
        uri, params = response.location.split('?')

        assert uri == oauth.default_redirect_uri

    def test_authorization_grant_token(self, client, oauth):
        client.login()

        response = client.post(url_for(
            'oauth.authorize',
            response_type='code',
            client_id=oauth.client_id,
        ), {
            'scope': 'default',
            'accept': '',
        })

        uri, params = response.location.split('?')
        code = parse_qs(params)['code'][0]

        client.logout()
        response = client.post(url_for('oauth.token'), {
            'grant_type': 'authorization_code',
            'code': code,
        }, headers=basic_header(oauth))

        assert200(response)
        assert response.content_type == 'application/json'
        assert 'access_token' in response.json

    def test_s256_code_challenge_success_client_secret_basic(self, client, oauth):
        code_verifier = generate_token(48)
        code_challenge = create_s256_code_challenge(code_verifier)

        client.login()

        response = client.post(url_for(
            'oauth.authorize',
            response_type='code',
            client_id=oauth.client_id,
            code_challenge=code_challenge,
            code_challenge_method='S256'
        ), {
            'scope': 'default',
            'accept': '',
        })
        assert 'code=' in response.location

        params = dict(url_decode(urlparse.urlparse(response.location).query))
        code = params['code']

        response = client.post(url_for('oauth.token'), {
            'grant_type': 'authorization_code',
            'code': code,
            'code_verifier': code_verifier
        }, headers=basic_header(oauth))

        assert200(response)
        assert response.content_type == 'application/json'
        assert 'access_token' in response.json

        token = response.json['access_token']

        response = client.post(url_for('api.fake'), headers={
            'Authorization': ' '.join(['Bearer', token])
        })

        assert200(response)
        assert response.content_type == 'application/json'
        assert response.json == {'success': True}

    def test_s256_code_challenge_success_client_secret_post(self, client, oauth):
        code_verifier = generate_token(48)
        code_challenge = create_s256_code_challenge(code_verifier)

        client.login()

        response = client.post(url_for(
            'oauth.authorize',
            response_type='code',
            client_id=oauth.client_id,
            code_challenge=code_challenge,
            code_challenge_method='S256'
        ), {
            'scope': 'default',
            'accept': '',
        })
        assert 'code=' in response.location

        params = dict(url_decode(urlparse.urlparse(response.location).query))
        code = params['code']

        response = client.post(url_for('oauth.token'), {
            'grant_type': 'authorization_code',
            'code': code,
            'code_verifier': code_verifier,
            'client_id': oauth.client_id,
            'client_secret': oauth.secret
        })

        assert200(response)
        assert response.content_type == 'application/json'
        assert 'access_token' in response.json

        token = response.json['access_token']

        response = client.post(url_for('api.fake'), headers={
            'Authorization': ' '.join(['Bearer', token])
        })

        assert200(response)
        assert response.content_type == 'application/json'
        assert response.json == {'success': True}

    def test_authorization_multiple_grant_token(self, client, oauth):

        for i in range(3):
            client.login()
            response = client.post(url_for(
                'oauth.authorize',
                response_type='code',
                client_id=oauth.client_id,
            ), {
                'scope': 'default',
                'accept': '',
            })

            uri, params = response.location.split('?')
            code = parse_qs(params)['code'][0]

            client.logout()
            response = client.post(url_for('oauth.token'), {
                'grant_type': 'authorization_code',
                'code': code,
            }, headers=basic_header(oauth))

            assert200(response)
            assert response.content_type == 'application/json'
            assert 'access_token' in response.json

    def test_authorization_grant_token_body_credentials(self, client, oauth):
        client.login()

        response = client.post(url_for(
            'oauth.authorize',
            response_type='code',
            client_id=oauth.client_id,
        ), {
            'scope': 'default',
            'accept': '',
        })

        uri, params = response.location.split('?')
        code = parse_qs(params)['code'][0]

        client.logout()
        response = client.post(url_for('oauth.token'), {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': oauth.client_id,
            'client_secret': oauth.secret,
        })

        assert200(response)
        assert response.content_type == 'application/json'
        assert 'access_token' in response.json

    @pytest.mark.oauth(internal=True)
    def test_authorization_redirects_for_internal_clients(self, client, oauth):
        client.login()

        response = client.get(url_for(
            'oauth.authorize',
            response_type='code',
            client_id=oauth.client_id,
            redirect_uri=oauth.default_redirect_uri
        ))

        assert_status(response, 302)
        uri, params = response.location.split('?')

        assert uri == oauth.default_redirect_uri
        assert 'code' in parse_qs(params)

    def test_client_credentials_grant_token(self, client, oauth):
        response = client.post(url_for('oauth.token'), {
            'grant_type': 'client_credentials',
        }, headers=basic_header(oauth))

        assert200(response)
        assert response.content_type == 'application/json'
        assert 'access_token' in response.json

    def test_password_grant_token(self, client, oauth):
        user = UserFactory(password='password')

        response = client.post(url_for('oauth.token'), {
            'grant_type': 'password',
            'username': user.email,
            'password': 'password',
        }, headers=basic_header(oauth))

        assert200(response)
        assert response.content_type == 'application/json'
        assert 'access_token' in response.json

    def test_invalid_implicit_grant_token(self, client, oauth):
        client.login()
        response = client.post(url_for(
            'oauth.authorize',
            response_type='token',
            client_id=oauth.client_id,
        ), {
            'accept': '',
        })

        assert_status(response, 400)
        assert response.json['error'] == 'invalid_grant'

    @pytest.mark.oauth(confidential=True)
    def test_refresh_token(self, client, oauth):
        user = UserFactory()
        token = OAuth2Token.objects.create(
            client=oauth,
            user=user,
            access_token='access-token',
            refresh_token='refresh-token',
        )

        response = client.post(url_for('oauth.token'), {
            'grant_type': 'refresh_token',
            'refresh_token': token.refresh_token,
        }, headers=basic_header(oauth))

        assert200(response)
        assert response.content_type == 'application/json'
        assert 'access_token' in response.json

    @pytest.mark.parametrize('token_type', ['access_token', 'refresh_token'])
    def test_revoke_token(self, client, oauth, token_type):
        user = UserFactory()
        token = OAuth2Token.objects.create(
            client=oauth,
            user=user,
            access_token='access-token',
            refresh_token='refresh-token',
        )
        response = client.post(url_for('oauth.revoke_token'), {
            'token': getattr(token, token_type),
        }, headers=basic_header(oauth))

        assert200(response)

        tok = OAuth2Token.objects(pk=token.pk).first()
        assert tok.revoked is True

    @pytest.mark.parametrize('token_type', ['access_token', 'refresh_token'])
    def test_revoke_token_with_hint(self, client, oauth, token_type):
        user = UserFactory()
        token = OAuth2Token.objects.create(
            client=oauth,
            user=user,
            access_token='access-token',
            refresh_token='refresh-token',
        )
        response = client.post(url_for('oauth.revoke_token'), {
            'token': getattr(token, token_type),
            'token_type_hint': token_type
        }, headers=basic_header(oauth))
        assert200(response)

        tok = OAuth2Token.objects(pk=token.pk).first()
        assert tok.revoked is True

    def test_revoke_token_with_bad_hint(self, client, oauth):
        user = UserFactory()
        token = OAuth2Token.objects.create(
            client=oauth,
            user=user,
            access_token='access-token',
            refresh_token='refresh-token',
        )

        response = client.post(url_for('oauth.revoke_token'), {
            'token': token.access_token,
            'token_type_hint': 'refresh_token',
        }, headers=basic_header(oauth))
        assert200(response)

        tok = OAuth2Token.objects(pk=token.pk).first()
        assert tok.revoked is False

    def test_value_error(self, api):
        @ns.route('/exception', endpoint='exception')
        class ExceptionAPI(API):
            def get(self):
                raise ValueError('Not working')

        response = api.get(url_for('api.exception'))

        assert400(response)
        assert response.json['message'] == 'Not working'

    def test_permission_denied(self, api):
        @ns.route('/exception', endpoint='exception')
        class ExceptionAPI(API):
            def get(self):
                raise PermissionDenied('Permission denied')

        response = api.get(url_for('api.exception'))

        assert403(response)
        assert 'message' in response.json
