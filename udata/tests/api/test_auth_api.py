from datetime import datetime
from urllib.parse import parse_qs

import pytest
from authlib.common.security import generate_token
from authlib.common.urls import url_decode, urlparse
from authlib.oauth2.rfc7636 import (
    create_s256_code_challenge,
)
from flask import current_app, url_for

from udata.api import API, api
from udata.api.factories import CLIENT_SECRET, OAuth2TokenFactory
from udata.api.oauth2 import OAuth2Client, OAuth2Token
from udata.auth import PermissionDenied
from udata.core.api_token.hashing import hash_token
from udata.core.api_token.models import ApiToken
from udata.core.user.factories import UserFactory
from udata.core.user.models import User
from udata.forms import Form, fields, validators
from udata.tests.api import PytestOnlyAPITestCase, basic_header
from udata.tests.helpers import (
    assert200,
    assert400,
    assert401,
    assert403,
    assert_status,
)

ns = api.namespace("fake", "A Fake namespace")


class FakeForm(Form):
    required = fields.StringField(validators=[validators.DataRequired()])
    choices = fields.SelectField(choices=["first", "second"])
    email = fields.StringField(validators=[validators.Email()])


@ns.route("/", endpoint="fake")
class FakeAPI(API):
    @api.secure
    def post(self):
        return {"success": True}

    def get(self):
        return {"success": True}

    def put(self):
        api.validate(FakeForm)
        return {"success": True}


@pytest.fixture
def oauth(app, request):
    marker = request.node.get_closest_marker("oauth")
    custom_kwargs = marker.kwargs if marker else {}
    kwargs = dict(
        name="test-client",
        owner=UserFactory(),
        redirect_uris=["https://test.org/callback"],
        secret=hash_token(CLIENT_SECRET),
    )
    kwargs.update(custom_kwargs)
    return OAuth2Client.objects.create(**kwargs)


class APIAuthTest(PytestOnlyAPITestCase):
    def test_no_auth(self):
        """Should not return a content type if there is no content on delete"""
        response = self.get(url_for("api.fake"))

        assert200(response)
        assert response.content_type == "application/json"
        assert response.json == {"success": True}

    def test_session_auth(self):
        """Should handle session authentication"""
        self.login()  # Session auth

        response = self.post(url_for("api.fake"))

        assert200(response)
        assert response.content_type == "application/json"
        assert response.json == {"success": True}

    def test_header_auth(self):
        """Should handle header API Key authentication"""
        with self.api_user():
            response = self.post(url_for("api.fake"))

        assert200(response)
        assert response.content_type == "application/json"
        assert response.json == {"success": True}

    def test_oauth_auth(self, oauth):
        """Should handle OAuth header authentication"""
        OAuth2TokenFactory(client=oauth, access="access-token", refresh="refresh-token")

        response = self.post(url_for("api.fake"), headers={"Authorization": "Bearer access-token"})

        assert200(response)
        assert response.content_type == "application/json"
        assert response.json == {"success": True}

    def test_oauth_auth_refuses_the_stored_tokens(self, oauth):
        # What a dump of the database gives.
        token = OAuth2TokenFactory(client=oauth, access="access-token", refresh="refresh-token")

        response = self.post(
            url_for("api.fake"), headers={"Authorization": f"Bearer {token.access_token}"}
        )
        assert401(response)

        response = self.post(
            url_for("oauth.token"),
            {"grant_type": "refresh_token", "refresh_token": token.refresh_token},
            headers=basic_header(oauth),
            json=False,
        )
        assert400(response)
        assert response.json["error"] == "invalid_grant"

    def test_bad_oauth_auth(self, oauth):
        """Should handle wrong OAuth header authentication"""
        OAuth2TokenFactory(client=oauth, access="access-token", refresh="refresh-token")

        response = self.post(
            url_for("api.fake"), headers={"Authorization": " ".join(["Bearer", "not-my-token"])}
        )

        assert401(response)
        assert response.content_type == "application/json"

    def test_no_apikey(self):
        """Should raise a HTTP 401 if no API Key is provided"""
        response = self.post(url_for("api.fake"))

        assert401(response)
        assert response.content_type == "application/json"
        assert "message" in response.json

    def test_invalid_apikey(self):
        """Should raise a HTTP 401 if an invalid API Key is provided"""
        response = self.post(url_for("api.fake"), headers={"X-API-KEY": "fake"})

        assert401(response)
        assert response.content_type == "application/json"
        assert "message" in response.json

    def test_inactive_user(self):
        """Should raise a HTTP 401 if the user is inactive"""
        user = UserFactory(active=False)
        with self.api_user(user):
            response = self.post(url_for("api.fake"))

        assert401(response)
        assert response.content_type == "application/json"
        assert "message" in response.json

    def test_deleted_user(self):
        """Should raise a HTTP 401 if the user is deleted"""
        from udata.core.api_token.models import ApiToken

        user = UserFactory()
        token, plaintext = ApiToken.generate(user)
        user.mark_as_deleted()
        response = self.post(url_for("api.fake"), headers={"X-API-KEY": plaintext})

        assert401(response)
        assert response.content_type == "application/json"
        assert "message" in response.json

    def test_validation_errors(self):
        """Should raise a HTTP 400 and returns errors on validation error"""
        response = self.put(url_for("api.fake"), {"email": "wrong"})

        assert400(response)
        assert response.content_type == "application/json"

        for field in "required", "email", "choices":
            assert field in response.json["errors"]
            assert isinstance(response.json["errors"][field], list)

    def test_no_validation_error(self):
        """Should pass if no validation error"""
        response = self.put(
            url_for("api.fake"),
            {
                "required": "value",
                "email": "coucou@cmoi.fr",
                "choices": "first",
            },
        )

        assert200(response)
        assert response.json == {"success": True}

    def test_authorization_head(self, oauth):
        """Should answer HEAD requests, which Flask routes alongside GET"""
        self.login()

        response = self.client.head(
            url_for(
                "oauth.authorize",
                response_type="code",
                client_id=oauth.client_id,
                redirect_uri=oauth.default_redirect_uri,
                code_challenge=create_s256_code_challenge(generate_token(48)),
                code_challenge_method="S256",
            )
        )

        assert200(response)
        assert response.data == b""

    def test_authorization_decline(self, oauth):
        """Should redirect to the redirect_uri on authorization denied"""
        self.login()

        response = self.post(
            url_for(
                "oauth.authorize",
                response_type="code",
                client_id=oauth.client_id,
                redirect_uri=oauth.default_redirect_uri,
            ),
            {
                "scope": "default",
                "refuse": "",
            },
            json=False,
        )

        assert_status(response, 302)
        uri, params = response.location.split("?")
        assert uri == oauth.default_redirect_uri

    def test_authorization_accept(self, oauth):
        """Should redirect to the redirect_uri on authorization accepted"""
        self.login()

        response = self.post(
            url_for(
                "oauth.authorize",
                response_type="code",
                client_id=oauth.client_id,
                redirect_uri=oauth.default_redirect_uri,
            ),
            {
                "scope": "default",
                "accept": "",
            },
            json=False,
        )

        assert_status(response, 302)
        uri, params = response.location.split("?")

        assert uri == oauth.default_redirect_uri

    @pytest.mark.options(OAUTH2_ALLOW_WILDCARD_IN_REDIRECT_URI=True)
    @pytest.mark.oauth(redirect_uris=["https://*.test.org/callback"])
    def test_authorization_accept_wildcard(self, oauth):
        """Should redirect to the redirect_uri on authorization accepted
        with wildcard enabled and used in config"""
        self.login()

        redirect_uri = "https://subdomain.test.org/callback"

        response = self.post(
            url_for(
                "oauth.authorize",
                response_type="code",
                client_id=oauth.client_id,
                redirect_uri=redirect_uri,
            ),
            {
                "scope": "default",
                "accept": "",
            },
            json=False,
        )

        assert_status(response, 302)
        uri, _ = response.location.split("?")

        assert uri == redirect_uri

    @pytest.mark.options(OAUTH2_ALLOW_WILDCARD_IN_REDIRECT_URI=False)
    @pytest.mark.oauth(redirect_uris=["https://*.test.org/callback"])
    def test_authorization_accept_no_wildcard(self, oauth):
        """Should not redirect to the redirect_uri on authorization accepted
        without wildcard enabled while used in config"""
        self.login()

        redirect_uri = "https://subdomain.test.org/callback"

        response = self.post(
            url_for(
                "oauth.authorize",
                response_type="code",
                client_id=oauth.client_id,
                redirect_uri=redirect_uri,
            ),
            {
                "scope": "default",
                "accept": "",
            },
            json=False,
        )

        assert_status(response, 400)
        assert "error" in response.json
        assert "Redirect URI" in response.json["error_description"]

    @pytest.mark.options(OAUTH2_ALLOW_WILDCARD_IN_REDIRECT_URI=True)
    @pytest.mark.oauth(redirect_uris=["https://*.test.org/callback"])
    def test_authorization_accept_wrong_wildcard(self, oauth):
        """Should not redirect to the redirect_uri on authorization accepted
        with wildcard enabled but mismatched from config"""
        self.login()

        redirect_uri = "https://subdomain.example.com/callback"

        response = self.post(
            url_for(
                "oauth.authorize",
                response_type="code",
                client_id=oauth.client_id,
                redirect_uri=redirect_uri,
            ),
            {
                "scope": "default",
                "accept": "",
            },
            json=False,
        )

        assert_status(response, 400)
        assert "error" in response.json
        assert "Redirect URI" in response.json["error_description"]

    @pytest.mark.parametrize(
        "client_id", ["", "x", "dataset:6853c089b3ed5781f6adfdf7", "6853c089b3ed5781f6adfdf7"]
    )
    def test_authorization_unusable_client_id(self, client_id):
        """Whether it parses as an ObjectId or not, a `client_id` we have no
        client for gets the OAuth error response — so the consent screen shows
        its error state instead of prompting for an undefined app. The response
        keeps authlib's headers, since its body reflects the client's `state`."""
        self.login()

        response = self.get(url_for("oauth.authorize", response_type="code", client_id=client_id))

        assert400(response)
        assert response.json["error"] == "invalid_client"
        assert response.headers["Cache-Control"] == "no-store"

    @pytest.mark.parametrize(
        "client_id", ["", "x", "dataset:6853c089b3ed5781f6adfdf7", "6853c089b3ed5781f6adfdf7"]
    )
    def test_client_info_unusable_client_id(self, client_id):
        """Same for the endpoint the consent screen actually calls."""
        self.login()

        response = self.get(url_for("oauth.client_info", response_type="code", client_id=client_id))

        assert400(response)
        assert response.json["error"] == "invalid_client"
        assert response.headers["Cache-Control"] == "no-store"

    def test_token_malformed_client_id(self):
        """A malformed `client_id` is an unknown client, not a server error."""
        response = self.post(
            url_for("oauth.token"),
            {
                "grant_type": "authorization_code",
                "code": "whatever",
                "client_id": "x",
            },
            json=False,
        )

        assert400(response)
        assert response.json["error"] == "invalid_client"

    def test_authorization_grant_token(self, oauth):
        self.login()

        response = self.post(
            url_for(
                "oauth.authorize",
                response_type="code",
                client_id=oauth.client_id,
            ),
            {
                "scope": "default",
                "accept": "",
            },
            json=False,
        )

        uri, params = response.location.split("?")
        code = parse_qs(params)["code"][0]

        self.logout()
        response = self.post(
            url_for("oauth.token"),
            {
                "grant_type": "authorization_code",
                "code": code,
            },
            headers=basic_header(oauth),
            json=False,
        )

        assert200(response)
        assert response.content_type == "application/json"
        assert "access_token" in response.json
        # A token has been created and saved, hashed.
        assert OAuth2Token.objects(access_token=response.json["access_token"]).count() == 0
        tokens = OAuth2Token.objects(access_token=hash_token(response.json["access_token"]))
        assert len(tokens) == 1
        assert tokens[0].refresh_token == hash_token(response.json["refresh_token"])

    def test_s256_code_challenge_success_client_secret_basic(self, oauth):
        code_verifier = generate_token(48)
        code_challenge = create_s256_code_challenge(code_verifier)

        self.login()

        response = self.post(
            url_for(
                "oauth.authorize",
                response_type="code",
                client_id=oauth.client_id,
                code_challenge=code_challenge,
                code_challenge_method="S256",
            ),
            {
                "scope": "default",
                "accept": "",
            },
            json=False,
        )
        assert "code=" in response.location

        params = dict(url_decode(urlparse.urlparse(response.location).query))
        code = params["code"]

        response = self.post(
            url_for("oauth.token"),
            {"grant_type": "authorization_code", "code": code, "code_verifier": code_verifier},
            headers=basic_header(oauth),
            json=False,
        )

        assert200(response)
        assert response.content_type == "application/json"
        assert "access_token" in response.json

        token = response.json["access_token"]

        response = self.post(
            url_for("api.fake"), headers={"Authorization": " ".join(["Bearer", token])}
        )

        assert200(response)
        assert response.content_type == "application/json"
        assert response.json == {"success": True}

    def test_s256_code_challenge_success_client_secret_post(self, oauth):
        code_verifier = generate_token(48)
        code_challenge = create_s256_code_challenge(code_verifier)

        self.login()

        response = self.post(
            url_for(
                "oauth.authorize",
                response_type="code",
                client_id=oauth.client_id,
                code_challenge=code_challenge,
                code_challenge_method="S256",
            ),
            {
                "scope": "default",
                "accept": "",
            },
            json=False,
        )
        assert "code=" in response.location

        params = dict(url_decode(urlparse.urlparse(response.location).query))
        code = params["code"]

        response = self.post(
            url_for("oauth.token"),
            {
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
                "client_id": oauth.client_id,
                "client_secret": CLIENT_SECRET,
            },
            json=False,
        )

        assert200(response)
        assert response.content_type == "application/json"
        assert "access_token" in response.json

        token = response.json["access_token"]

        response = self.post(
            url_for("api.fake"), headers={"Authorization": " ".join(["Bearer", token])}
        )

        assert200(response)
        assert response.content_type == "application/json"
        assert response.json == {"success": True}

    @pytest.mark.oauth(secret=None)
    def test_s256_code_challenge_success_no_client_secret(self, oauth):
        """Authenticate through an OAuth client that has no secret associated (public client)"""
        code_verifier = generate_token(48)
        code_challenge = create_s256_code_challenge(code_verifier)

        self.login()

        response = self.post(
            url_for(
                "oauth.authorize",
                response_type="code",
                client_id=oauth.client_id,
                code_challenge=code_challenge,
                code_challenge_method="S256",
            ),
            {
                "scope": "default",
                "accept": "",
            },
            json=False,
        )
        assert "code=" in response.location

        params = dict(url_decode(urlparse.urlparse(response.location).query))
        code = params["code"]

        response = self.post(
            url_for("oauth.token"),
            {
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
                "client_id": oauth.client_id,
            },
            json=False,
        )

        assert200(response)
        assert response.content_type == "application/json"
        assert "access_token" in response.json

        token = response.json["access_token"]

        response = self.post(
            url_for("api.fake"), headers={"Authorization": " ".join(["Bearer", token])}
        )

        assert200(response)
        assert response.content_type == "application/json"
        assert response.json == {"success": True}

    def test_s256_code_challenge_missing_client_secret(self, oauth):
        """Fail authentication through an OAuth client with missing secret"""
        code_verifier = generate_token(48)
        code_challenge = create_s256_code_challenge(code_verifier)

        self.login()

        response = self.post(
            url_for(
                "oauth.authorize",
                response_type="code",
                client_id=oauth.client_id,
                code_challenge=code_challenge,
                code_challenge_method="S256",
            ),
            {
                "scope": "default",
                "accept": "",
            },
            json=False,
        )
        assert "code=" in response.location

        params = dict(url_decode(urlparse.urlparse(response.location).query))
        code = params["code"]

        response = self.post(
            url_for("oauth.token"),
            {
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
                "client_id": oauth.client_id,
            },
            json=False,
        )

        assert401(response)

    def test_authorization_multiple_grant_token(self, oauth):
        for i in range(3):
            self.login()
            response = self.post(
                url_for(
                    "oauth.authorize",
                    response_type="code",
                    client_id=oauth.client_id,
                ),
                {
                    "scope": "default",
                    "accept": "",
                },
                json=False,
            )

            uri, params = response.location.split("?")
            code = parse_qs(params)["code"][0]

            self.logout()
            response = self.post(
                url_for("oauth.token"),
                {
                    "grant_type": "authorization_code",
                    "code": code,
                },
                headers=basic_header(oauth),
                json=False,
            )

            assert200(response)
            assert response.content_type == "application/json"
            assert "access_token" in response.json

    def test_authorization_grant_token_body_credentials(self, oauth):
        self.login()

        response = self.post(
            url_for(
                "oauth.authorize",
                response_type="code",
                client_id=oauth.client_id,
            ),
            {
                "scope": "default",
                "accept": "",
            },
            json=False,
        )

        uri, params = response.location.split("?")
        code = parse_qs(params)["code"][0]

        self.logout()
        response = self.post(
            url_for("oauth.token"),
            {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": oauth.client_id,
                "client_secret": CLIENT_SECRET,
            },
            json=False,
        )

        assert200(response)
        assert response.content_type == "application/json"
        assert "access_token" in response.json

    @pytest.mark.oauth(internal=True)
    def test_authorization_redirects_for_internal_clients(self, oauth):
        self.login()

        response = self.get(
            url_for(
                "oauth.authorize",
                response_type="code",
                client_id=oauth.client_id,
                redirect_uri=oauth.default_redirect_uri,
            )
        )

        assert_status(response, 302)
        uri, params = response.location.split("?")

        assert uri == oauth.default_redirect_uri
        assert "code" in parse_qs(params)

    def test_client_credentials_grant_token(self, oauth):
        response = self.post(
            url_for("oauth.token"),
            {
                "grant_type": "client_credentials",
            },
            headers=basic_header(oauth),
            json=False,
        )

        assert200(response)
        assert response.content_type == "application/json"
        assert "access_token" in response.json

    def test_client_credentials_grant_refuses_a_wrong_secret(self, oauth):
        response = self.post(
            url_for("oauth.token"),
            {"grant_type": "client_credentials"},
            headers=basic_header(oauth, "wrong-secret"),
            json=False,
        )

        assert401(response)
        assert response.json["error"] == "invalid_client"

    def test_client_credentials_grant_refuses_the_stored_secret(self, oauth):
        # What a dump of the database gives.
        response = self.post(
            url_for("oauth.token"),
            {"grant_type": "client_credentials"},
            headers=basic_header(oauth, oauth.secret),
            json=False,
        )

        assert401(response)
        assert response.json["error"] == "invalid_client"

    @pytest.mark.oauth(secret=None)
    def test_client_credentials_grant_refuses_a_secret_for_a_public_client(self, oauth):
        response = self.post(
            url_for("oauth.token"),
            {"grant_type": "client_credentials"},
            headers=basic_header(oauth),
            json=False,
        )

        assert401(response)
        assert response.json["error"] == "invalid_client"

    def test_create_oauth_client_prints_the_secret_it_stores_hashed(self):
        user = UserFactory()

        result = self.cli("api", "create-oauth-client", "-u", user.email)

        secret = result.output.split("Client's secret ")[1].split()[0]
        client = OAuth2Client.objects.get(owner=user)
        assert client.secret == hash_token(secret)
        response = self.post(
            url_for("oauth.token"),
            {"grant_type": "client_credentials"},
            headers=basic_header(client, secret),
            json=False,
        )
        assert200(response)

    def test_create_public_oauth_client_stores_no_secret(self):
        user = UserFactory()

        self.cli("api", "create-oauth-client", "-u", user.email, "-p")

        assert OAuth2Client.objects.get(owner=user).secret is None

    def test_password_grant_token(self, oauth):
        user = UserFactory(password="password")

        response = self.post(
            url_for("oauth.token"),
            {
                "grant_type": "password",
                "username": user.email,
                "password": "password",
            },
            headers=basic_header(oauth),
            json=False,
        )

        assert200(response)
        assert response.content_type == "application/json"
        assert "access_token" in response.json

    def test_invalid_implicit_grant_token(self, oauth):
        self.login()
        response = self.post(
            url_for(
                "oauth.authorize",
                response_type="token",
                client_id=oauth.client_id,
            ),
            {
                "accept": "",
            },
            json=False,
        )

        # Authlib 1.6.10+ redirects implicit grants to error instead of returning 400
        assert_status(response, 302)
        # Verify implicit grant is rejected with error parameter
        assert "error=unsupported_response_type" in response.location

    @pytest.mark.oauth(confidential=True)
    def test_refresh_token(self, oauth):
        user = UserFactory()
        token_to_be_refreshed = OAuth2TokenFactory(
            client=oauth, user=user, access="access-token", refresh="refresh-token"
        )
        token_same_user_not_refreshed = OAuth2TokenFactory(
            client=oauth,
            user=user,
            access="same-user-access-token",
            refresh="same-user-refresh-token",
        )
        other_token = OAuth2TokenFactory(
            client=oauth, access="other-access-token", refresh="other-refresh-token"
        )
        tokens_count = OAuth2Token.objects.count()

        response = self.post(
            url_for("oauth.token"),
            {
                "grant_type": "refresh_token",
                "refresh_token": "refresh-token",
            },
            headers=basic_header(oauth),
            json=False,
        )

        assert200(response)
        assert response.content_type == "application/json"
        assert "access_token" in response.json

        # Reload from the DB.
        token_to_be_refreshed.reload()
        token_same_user_not_refreshed.reload()
        other_token.reload()

        assert tokens_count == OAuth2Token.objects.count()  # No new token created.

        # Both tokens have been replaced by the hashes of the new ones.
        assert token_to_be_refreshed.access_token == hash_token(response.json["access_token"])
        assert token_to_be_refreshed.refresh_token == hash_token(response.json["refresh_token"])

        # No change to the user's other token.
        assert token_same_user_not_refreshed.access_token == hash_token("same-user-access-token")
        assert token_same_user_not_refreshed.refresh_token == hash_token("same-user-refresh-token")

        # No change to other token.
        assert other_token.access_token == hash_token("other-access-token")
        assert other_token.refresh_token == hash_token("other-refresh-token")

    @pytest.mark.parametrize("plaintext", ["access-token", "refresh-token"])
    def test_revoke_token(self, client, oauth, plaintext):
        token = OAuth2TokenFactory(client=oauth, access="access-token", refresh="refresh-token")
        response = self.post(
            url_for("oauth.revoke_token"),
            {
                "token": plaintext,
            },
            headers=basic_header(oauth),
            json=False,
        )

        assert200(response)

        tok = OAuth2Token.objects(pk=token.pk).first()
        assert tok.revoked is True

    @pytest.mark.parametrize(
        "token_type, plaintext",
        [("access_token", "access-token"), ("refresh_token", "refresh-token")],
    )
    def test_revoke_token_with_hint(self, client, oauth, token_type, plaintext):
        token = OAuth2TokenFactory(client=oauth, access="access-token", refresh="refresh-token")
        response = self.post(
            url_for("oauth.revoke_token"),
            {"token": plaintext, "token_type_hint": token_type},
            headers=basic_header(oauth),
            json=False,
        )
        assert200(response)

        tok = OAuth2Token.objects(pk=token.pk).first()
        assert tok.revoked is True

    def test_revoke_token_with_bad_hint(self, oauth):
        token = OAuth2TokenFactory(client=oauth, access="access-token", refresh="refresh-token")

        response = self.post(
            url_for("oauth.revoke_token"),
            {
                "token": "access-token",
                "token_type_hint": "refresh_token",
            },
            headers=basic_header(oauth),
            json=False,
        )
        assert200(response)

        tok = OAuth2Token.objects(pk=token.pk).first()
        assert tok.revoked is False

    def test_value_error(self):
        @ns.route("/exception", endpoint="exception")
        class ExceptionAPI(API):
            def get(self):
                raise ValueError("Not working")

        response = self.get(url_for("api.exception"))

        assert400(response)
        assert response.json["message"] == "Not working"

    def test_permission_denied(self):
        @ns.route("/exception", endpoint="exception")
        class ExceptionAPI(API):
            def get(self):
                raise PermissionDenied("Permission denied")

        response = self.get(url_for("api.exception"))

        assert403(response)
        assert "message" in response.json


# A cookie must reach the next request for its absence to prove anything: the test client
# speaks plain http to local.test, whatever a local udata.cfg says.
@pytest.mark.options(SESSION_COOKIE_SECURE=False, SESSION_COOKIE_DOMAIN=None)
class HeaderAuthTest(PytestOnlyAPITestCase):
    """A credential sent in a header authenticates its request only. A session it opened
    would outlive its revocation, and be fresh enough for the sensitive operations. Nor is
    it a login: the credential records its own use."""

    LAST_LOGIN = datetime(2024, 1, 1)

    def post(self, headers=None):
        # pytest-flask keeps one app context, hence one `g`, for the whole test, and
        # flask-login caches the user there: a context per request reads the cookie.
        with current_app.app_context():
            return self.client.post(url_for("api.fake"), headers=headers)

    def assert_authenticated_this_request_only(self, response, user):
        assert200(response)
        assert not response.headers.getlist("Set-Cookie")
        assert401(self.post())
        assert User.objects.get(id=user.id).current_login_at == self.LAST_LOGIN

    def test_api_key(self):
        user = UserFactory(current_login_at=self.LAST_LOGIN)
        token, plaintext = ApiToken.generate(user)

        self.assert_authenticated_this_request_only(self.post({"X-API-KEY": plaintext}), user)
        token.reload()
        assert token.last_used_at is not None

    def test_oauth_token(self, oauth):
        user = UserFactory(current_login_at=self.LAST_LOGIN)
        token = OAuth2TokenFactory(client=oauth, user=user, access="access-token")

        self.assert_authenticated_this_request_only(
            self.post({"Authorization": "Bearer access-token"}), user
        )
        token.reload()
        assert token.last_used_at is not None
