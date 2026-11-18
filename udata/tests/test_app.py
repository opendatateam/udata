import pytest
from flask import request
from werkzeug.exceptions import BadRequest

from udata.tests.api import PytestOnlyAPITestCase


class UdataJsonProviderTest(PytestOnlyAPITestCase):
    def test_too_deeply_nested_json_is_invalid_json(self):
        body = "[" * 300_000
        with self.app.test_request_context(
            method="POST", data=body, content_type="application/json"
        ):
            assert request.get_json(silent=True) is None
            with pytest.raises(BadRequest):
                request.get_json()
