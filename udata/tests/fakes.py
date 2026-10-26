"""In-memory stand-ins for the external services udata talks to.

A fake reproduces the behaviour of the real service and is inspected after the fact,
instead of being handed a canned response per test.
"""

import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from authlib.jose import JsonWebKey, jwt


@dataclass
class ProConnectSession:
    email: str
    auth_time: int


@dataclass
class ProConnectGrant:
    email: str
    # The jwt claims, signed into the id_token when the code is exchanged.
    id_token_claims: dict


class ProConnectFake:
    """An in-memory ProConnect.

    The agent has a ProConnect session, opened when they last authenticated there: it
    answers authorizations without asking them anything, unless `max_age=0` makes
    ProConnect authenticate them again (OpenID Connect Core, not measured on ProConnect
    yet: `honors_max_age` plays a provider that ignores it). `auth_time` is only returned
    when requested through `claims` (`returns_auth_time` plays a provider that never does).
    The id_token doesn't carry the email: it comes from the userinfo endpoint, as a
    signed jwt.
    """

    ISSUER = "https://proconnect.test/api/v2"
    METADATA_URL = f"{ISSUER}/.well-known/openid-configuration"

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.key = JsonWebKey.generate_key("RSA", 2048, is_private=True, options={"kid": "test"})
        self.honors_max_age = True
        self.returns_auth_time = True
        self._session: ProConnectSession | None = None
        self._grants: dict[str, ProConnectGrant] = {}
        self._access_tokens: dict[str, ProConnectGrant] = {}

    def mount(self, rmock) -> None:
        rmock.get(self.METADATA_URL, json=self._metadata())
        rmock.get(f"{self.ISSUER}/jwks", json={"keys": [self.key.as_dict()]})
        rmock.post(f"{self.ISSUER}/token", json=self._handle_token)
        rmock.get(f"{self.ISSUER}/userinfo", content=self._handle_userinfo)

    def agent_has_session(self, email: str, authenticated_at: int | None = None) -> None:
        """Open a ProConnect session for `email`, authenticated at `authenticated_at` (now by default)."""
        self._session = ProConnectSession(email, authenticated_at or int(time.time()))

    def authorize(self, authorize_url: str) -> dict:
        """Play the browser round-trip and return the callback query parameters."""
        params = self._params(authorize_url)
        if self.honors_max_age and params.get("max_age") == "0":
            self._session.auth_time = int(time.time())

        requested = json.loads(params.get("claims", "{}")).get("id_token", {})
        id_token_claims = {"acr": "eidas1", "nonce": params["nonce"]}
        if "auth_time" in requested and self.returns_auth_time:
            id_token_claims["auth_time"] = self._session.auth_time

        code = uuid4().hex
        self._grants[code] = ProConnectGrant(self._session.email, id_token_claims)
        return {"code": code, "state": params["state"]}

    def deny(self, authorize_url: str) -> dict:
        """Play the agent cancelling at ProConnect and return the callback query parameters."""
        return {"error": "access_denied", "state": self._params(authorize_url)["state"]}

    def _params(self, authorize_url: str) -> dict:
        return {key: values[0] for key, values in parse_qs(urlparse(authorize_url).query).items()}

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
        return jwt.encode({"alg": "RS256", "kid": "test"}, payload, self.key).decode()

    def _handle_token(self, request, context) -> dict:
        grant = self._grants.pop(parse_qs(request.text)["code"][0])
        access_token = uuid4().hex
        self._access_tokens[access_token] = grant
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "id_token": self._sign(grant.id_token_claims),
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
