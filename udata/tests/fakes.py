"""In-memory stand-ins for the external services udata talks to.

A fake reproduces the behaviour of the real service and is inspected after the fact,
instead of being handed a canned response per test.
"""

import time
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from joserfc import jwt
from joserfc.jwk import RSAKey


@dataclass
class ProConnectGrant:
    email: str
    nonce: str


class ProConnectFake:
    """An in-memory ProConnect, with the semantics measured on its integration environment.

    An open ProConnect session answers authorizations without asking the agent anything,
    whatever `max_age` or `prompt=login` say. Only signing out (`end_session`, which
    also closes the session at the agent's identity provider) makes the next
    authorization authenticate them again: `authentications` counts those. Signing out
    with the id_token of a session already closed, even expired, comes back all the same.
    The id_token doesn't carry the email: it comes from the userinfo endpoint, as a
    signed jwt.
    """

    ISSUER = "https://proconnect.test/api/v2"
    METADATA_URL = f"{ISSUER}/.well-known/openid-configuration"

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.key = RSAKey.generate_key(2048, parameters={"kid": "test"}, private=True)
        # The ProConnect account of whoever is at the keyboard.
        self.agent: str | None = None
        self.session_open = False
        self.authentications = 0
        self._grants: dict[str, ProConnectGrant] = {}
        self._access_tokens: dict[str, ProConnectGrant] = {}

    def mount(self, rmock) -> None:
        rmock.get(self.METADATA_URL, json=self._metadata())
        rmock.get(f"{self.ISSUER}/jwks", json={"keys": [self.key.as_dict(private=False)]})
        rmock.post(f"{self.ISSUER}/token", json=self._handle_token)
        rmock.get(f"{self.ISSUER}/userinfo", content=self._handle_userinfo)

    def agent_has_session(self, email: str) -> None:
        """Put `email` at the keyboard, with a ProConnect session already open."""
        self.agent = email
        self.session_open = True

    def authorize(self, authorize_url: str) -> dict:
        """Play the browser round-trip and return the callback query parameters."""
        params = self._params(authorize_url)
        if not self.session_open:
            self.authentications += 1
            self.session_open = True

        code = uuid4().hex
        self._grants[code] = ProConnectGrant(self.agent, params["nonce"])
        return {"code": code, "state": params["state"]}

    def deny(self, authorize_url: str) -> dict:
        """Play the agent cancelling at ProConnect and return the callback query parameters."""
        return {"error": "access_denied", "state": self._params(authorize_url)["state"]}

    def end_session(self, end_session_url: str) -> dict:
        """Play the sign-out round-trip and return the post-logout query parameters."""
        params = self._params(end_session_url)
        assert params["id_token_hint"]
        self.session_open = False
        return {"state": params["state"]}

    def _params(self, url: str) -> dict:
        return {key: values[0] for key, values in parse_qs(urlparse(url).query).items()}

    def _metadata(self) -> dict:
        return {
            "issuer": self.ISSUER,
            "authorization_endpoint": f"{self.ISSUER}/authorize",
            "token_endpoint": f"{self.ISSUER}/token",
            "userinfo_endpoint": f"{self.ISSUER}/userinfo",
            "jwks_uri": f"{self.ISSUER}/jwks",
            "end_session_endpoint": f"{self.ISSUER}/session/end",
            "id_token_signing_alg_values_supported": ["RS256"],
        }

    def _sign(self, claims: dict) -> str:
        now = int(time.time())
        payload = {
            "iss": self.ISSUER,
            "aud": self.client_id,
            "sub": "agent-sub",
            "iat": now,
            "exp": now + 60,
            **claims,
        }
        return jwt.encode({"alg": "RS256", "kid": "test"}, payload, self.key)

    def _handle_token(self, request, context) -> dict:
        grant = self._grants.pop(parse_qs(request.text)["code"][0])
        access_token = uuid4().hex
        self._access_tokens[access_token] = grant
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "id_token": self._sign({"acr": "eidas1", "nonce": grant.nonce}),
        }

    def _handle_userinfo(self, request, context) -> bytes:
        grant = self._access_tokens[request.headers["Authorization"].removeprefix("Bearer ")]
        context.headers["Content-Type"] = "application/jwt"
        return self._sign(
            {"email": grant.email, "given_name": "Jane", "usual_name": "Doe"}
        ).encode()


class DataCiteFake:
    """An in-memory DOI registry, with the semantics measured on api.test.datacite.org.

    `PUT /dois/{doi}` upserts: 201 when the DOI is new, 200 when it already exists.
    `event: publish` makes the DOI findable, and a later PUT without `event` leaves it
    findable rather than dropping it back to draft.
    """

    def __init__(self):
        self.dois: dict[str, dict] = {}
        self.requests: list[dict] = []
        self._failure: int | None = None

    def fails_with(self, status_code: int) -> None:
        """Make every subsequent call answer `status_code`, as an unreachable or upset API would."""
        self._failure = status_code

    def handle_put(self, request, context) -> dict:
        if self._failure:
            context.status_code = self._failure
            return {"errors": [{"title": "DataCite is unhappy"}]}

        doi = request.path.removeprefix("/dois/")
        attributes = request.json()["data"]["attributes"]
        self.requests.append(attributes)

        context.status_code = 200 if doi in self.dois else 201
        record = self.dois.setdefault(doi, {"state": "draft"})
        record.update({key: value for key, value in attributes.items() if key != "event"})
        if attributes.get("event") == "publish":
            record["state"] = "findable"
        return {"data": {"attributes": record}}
