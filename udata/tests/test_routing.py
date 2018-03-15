# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from uuid import uuid4, UUID

from flask import url_for


class UUIDConverterTest:
    @pytest.fixture(autouse=True)
    def setup(self, app):

        @app.route('/uuid/<uuid:uuid>')
        def uuid_tester(uuid):
            return 'ok'

    def test_serialize_uuid_to_url(self):
        uuid = uuid4()
        url = url_for('uuid_tester', uuid=uuid)
        assert url == '/uuid/{0}'.format(str(uuid))

    def test_serialize_string_uuid_to_url(self):
        uuid = uuid4()
        url = url_for('uuid_tester', uuid=str(uuid))
        assert url == '/uuid/{0}'.format(str(uuid))

    def test_resolve_uuid(self, client):
        uuid = uuid4()
        url = '/uuid/{0}'.format(str(uuid))
        assert client.get(url).data == 'ok'

    def test_resolve_uuid_with_spaces(self, client):
        uuid = uuid4()
        url = '/uuid/{0} '.format(str(uuid))
        assert client.get(url).data == 'ok'
