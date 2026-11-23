"""In-memory stand-ins for the external services udata talks to.

A fake reproduces the behaviour of the real service and is inspected after the fact,
instead of being handed a canned response per test.
"""

import json
import operator
import re
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlencode, urlparse, urlunparse
from uuid import uuid4

import requests
from joserfc import jwt
from joserfc.jwk import RSAKey


@dataclass
class ProConnectGrant:
    email: str
    sub: str
    nonce: str
    acr: str
    amr: list[str] | None


class ProConnectFake:
    """An in-memory ProConnect, with the semantics measured on its integration environment.

    An open ProConnect session answers authorizations without asking the agent anything,
    whatever `max_age` or `prompt=login` say. Only signing out (`end_session`, which
    also closes the session at the agent's identity provider) makes the next
    authorization authenticate them again: `authentications` counts those. Signing out
    with the id_token of a session already closed, even expired, comes back all the same.
    An `acr` required at a second factor level is the exception: a session opened
    without one makes the agent authenticate again, with a second factor this time.
    The `amr` tells how the session was opened (`pop` for a security key, `pwd` alone
    for a password), and only comes back when the `claims` ask for it. Each identity has
    its own `sub`, whatever its email. The id_token doesn't carry the email: it comes from
    the userinfo endpoint, as a signed jwt.
    """

    SECOND_FACTOR_ACR_VALUES = {"eidas0-mfa", "eidas1-mfa", "eidas2", "eidas3"}

    ISSUER = "https://proconnect.test/api/v2"
    METADATA_URL = f"{ISSUER}/.well-known/openid-configuration"

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.key = RSAKey.generate_key(2048, parameters={"kid": "test"}, private=True)
        # The ProConnect account of whoever is at the keyboard.
        self.agent: str | None = None
        self.agent_sub: str | None = None
        self.agent_amr: list[str] | None = None
        self.session_open = False
        self.session_second_factor = False
        self.authentications = 0
        self.second_factors = 0
        self._grants: dict[str, ProConnectGrant] = {}
        self._access_tokens: dict[str, ProConnectGrant] = {}

    def mount(self, rmock) -> None:
        rmock.get(self.METADATA_URL, json=self._metadata())
        rmock.get(f"{self.ISSUER}/jwks", json={"keys": [self.key.as_dict(private=False)]})
        rmock.post(f"{self.ISSUER}/token", json=self._handle_token)
        rmock.get(f"{self.ISSUER}/userinfo", content=self._handle_userinfo)

    def agent_has_session(
        self,
        email: str,
        second_factor: bool = True,
        sub: str | None = None,
        amr: list[str] | None = None,
    ) -> None:
        """Put the ProConnect identity of `email` at the keyboard, with a session already
        open. Another identity with the same email, such as one an attacker created, gets
        its own `sub`. `amr` is how the identity provider authenticates the agent, when it
        isn't a security key: a one-time code by email for one without a second factor."""
        self.agent = email
        self.agent_sub = sub or f"sub-of-{email}"
        self.agent_amr = amr
        self.session_open = True
        self.session_second_factor = second_factor

    def tamper(self, authorize_url: str, require_second_factor: bool) -> str:
        """What the agent's browser can do to the redirection to ProConnect before following
        it: require a second factor we don't, or drop the one we do."""
        params = self._params(authorize_url)
        if require_second_factor:
            params.pop("acr_values", None)
            claims = {"acr": {"essential": True, "values": ["eidas0-mfa"]}, "amr": None}
        else:
            params["acr_values"] = "eidas1"
            claims = {"amr": None}
        params["claims"] = json.dumps({"id_token": claims})
        return urlunparse(urlparse(authorize_url)._replace(query=urlencode(params)))

    def authorize(self, authorize_url: str) -> dict:
        """Play the browser round-trip and return the callback query parameters."""
        params = self._params(authorize_url)
        id_token_claims = json.loads(params.get("claims", "{}")).get("id_token", {})
        acr = id_token_claims.get("acr") or {}
        second_factor_required = acr.get("essential", False) and set(acr["values"]) <= (
            self.SECOND_FACTOR_ACR_VALUES
        )
        if not self.session_open or (second_factor_required and not self.session_second_factor):
            self.authentications += 1
            self.session_open = True
            self.session_second_factor = second_factor_required
            if second_factor_required:
                self.second_factors += 1

        # The `acr` is the level asked for, not the one reached: only a required one tells
        # that the agent presented a second factor.
        acr = "eidas0-mfa" if second_factor_required else "eidas1"
        amr = None
        if "amr" in id_token_claims:
            amr = self.agent_amr or (["pop", "mfa"] if self.session_second_factor else ["pwd"])
        code = uuid4().hex
        self._grants[code] = ProConnectGrant(self.agent, self.agent_sub, params["nonce"], acr, amr)
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
            "id_token": self._sign(
                {
                    "sub": grant.sub,
                    "acr": grant.acr,
                    "nonce": grant.nonce,
                    **({"amr": grant.amr} if grant.amr is not None else {}),
                }
            ),
        }

    def _handle_userinfo(self, request, context) -> bytes:
        grant = self._access_tokens[request.headers["Authorization"].removeprefix("Bearer ")]
        context.headers["Content-Type"] = "application/jwt"
        return self._sign(
            {"sub": grant.sub, "email": grant.email, "given_name": "Jane", "usual_name": "Doe"}
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


class TabularFake:
    """An in-memory api-tabular that answers like its `main` branch, for what tests send.

    A parameter it does not model raises `NotImplementedError`.
    """

    BASE_URL = "https://tabular.test"
    AGGREGATES = {
        "sum": lambda values: sum(values) if values else None,
        "count": len,
        "min": lambda values: min(values, default=None),
        "max": lambda values: max(values, default=None),
    }
    NUMERIC_TYPES = {"int", "float"}
    # `less` and `greater` include the bound, like api-tabular.
    ORDERINGS = {"less": operator.le, "greater": operator.ge}
    OPERATORS = {"groupby", "sort", "differs", *AGGREGATES, *ORDERINGS}

    def __init__(self):
        self.resources: dict[str, dict] = {}
        self.queries: list[str] = []
        self.profile_requests: list[str] = []
        self._failure: tuple[int, str] | None = None
        self._unreachable = False

    def mount(self, rmock) -> None:
        resource = f"^{re.escape(self.BASE_URL)}/api/resources/[^/]+"
        rmock.get(re.compile(f"{resource}/profile/$"), text=self._profile)
        rmock.get(re.compile(f"{resource}/data/"), text=self._data)

    def add_resource(self, rid, columns: dict[str, str], rows: list[dict] | None = None) -> None:
        """A resource of `columns` (`{name: python_type}`) holding `rows`."""
        self.resources[str(rid)] = {"columns": columns, "rows": rows or []}

    def fails_with(self, status_code: int, detail) -> None:
        """Make every subsequent call answer `status_code` with api-tabular's error body."""
        self._failure = (status_code, self._error("Invalid query", detail))

    def answers_unreadable(self) -> None:
        """Make every subsequent call answer 200 with a body of no expected shape."""
        self._failure = (200, json.dumps({"profile": None}))

    def unreachable(self) -> None:
        """Make every subsequent call fail on the network, after being recorded."""
        self._unreachable = True

    def recovers(self) -> None:
        self._unreachable = False

    @staticmethod
    def _error(title: str, detail) -> str:
        return json.dumps({"errors": [{"code": None, "title": title, "detail": detail}]})

    def _answer(self, rid: str, context) -> dict | str:
        """The resource, or the answer that replaces it."""
        if self._unreachable:
            raise requests.exceptions.ConnectionError("tabular.test is unreachable")
        if self._failure:
            context.status_code, body = self._failure
            return body
        if (resource := self.resources.get(rid)) is None:
            context.status_code = 404
            return "404: Not Found"
        return resource

    def _unknown_column(self, resource: dict, names: list[str], context) -> str | None:
        """api-tabular's 400 for the first of `names` the resource lacks, if any."""
        for name in names:
            if name not in resource["columns"]:
                context.status_code = 400
                return self._error("Database error", {"message": f"column {name} does not exist"})
        return None

    def _profile(self, request, context) -> str:
        rid = request.path.split("/")[3]
        self.profile_requests.append(rid)
        resource = self._answer(rid, context)
        if isinstance(resource, str):
            return resource
        columns = resource["columns"]
        return json.dumps(
            {
                "profile": {
                    "header": list(columns),
                    "columns": {name: {"python_type": kind} for name, kind in columns.items()},
                    "total_lines": len(resource["rows"]),
                }
            }
        )

    def _data(self, request, context) -> str:
        query = urlparse(request.url).query
        self.queries.append(query)
        resource = self._answer(request.path.split("/")[3], context)
        if isinstance(resource, str):
            return resource
        page, page_size = 1, 20
        columns = groupby = aggregate = sort = None
        rows = list(resource["rows"])
        for param in (param for param in query.split("&") if param):
            # The client encodes names and values twice so that `=` and `,` survive.
            raw_name, _, raw_value = param.partition("=")
            name, value = unquote(unquote(raw_name)), unquote(unquote(raw_value))
            if name == "page":
                page = int(value)
            elif name == "page_size":
                page_size = int(value)
            elif name == "columns":
                columns = [unquote(unquote(column)) for column in raw_value.split(",")]
                if unknown := self._unknown_column(resource, columns, context):
                    return unknown
            else:
                column, _, op = name.rpartition("__")
                if op not in self.OPERATORS:
                    raise NotImplementedError(f"TabularFake does not model {name}")
                if unknown := self._unknown_column(resource, [column], context):
                    return unknown
                if op == "groupby":
                    groupby = column
                elif op in self.AGGREGATES:
                    aggregate = (column, op)
                elif op == "sort":
                    sort = (column, value == "desc")
                elif op == "differs":
                    # Like PostgREST's `isdistinct`, it keeps the nulls.
                    rows = [
                        row for row in rows if row.get(column) is None or str(row[column]) != value
                    ]
                else:
                    if resource["columns"][column] not in self.NUMERIC_TYPES:
                        raise NotImplementedError("TabularFake orders numeric columns only")
                    compare = self.ORDERINGS[op]
                    rows = [
                        row
                        for row in rows
                        if row.get(column) is not None and compare(float(row[column]), float(value))
                    ]
        if aggregate:
            rows = self._aggregate(rows, groupby, aggregate)
        elif columns:
            rows = [{name: row.get(name) for name in columns} for row in rows]
        if sort:
            column, descending = sort
            rows.sort(
                key=lambda row: (row.get(column) is None, row.get(column)), reverse=descending
            )
        start = (page - 1) * page_size
        next_url = None
        if len(rows) > start + page_size:
            kept = [param for param in query.split("&") if param and not param.startswith("page=")]
            next_query = "&".join([*kept, f"page={page + 1}"])
            next_url = urlunparse(urlparse(request.url)._replace(query=next_query))
        body = {"data": rows[start : start + page_size], "links": {"next": next_url}, "meta": {}}
        if not aggregate:
            body["meta"]["total"] = len(rows)
        return json.dumps(body)

    def _aggregate(self, rows, groupby, aggregate):
        column, op = aggregate
        groups: dict = {}
        for row in rows:
            groups.setdefault(row.get(groupby) if groupby else None, []).append(row)
        if not groupby:
            groups = {None: rows}
        result = []
        for key, members in groups.items():
            values = [row[column] for row in members if row.get(column) is not None]
            out = {groupby: key} if groupby else {}
            out[f"{column}__{op}"] = self.AGGREGATES[op](values)
            result.append(out)
        return result
