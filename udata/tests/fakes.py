"""In-memory stand-ins for the external services udata talks to.

A fake reproduces the behaviour of the real service and is inspected after the fact,
instead of being handed a canned response per test.
"""


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
