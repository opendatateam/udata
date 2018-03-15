# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from bson import ObjectId
from uuid import uuid4

from flask import url_for

from udata import routing
from udata.models import db


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


class Tester(db.Document):
    slug = db.StringField()


class TesterConverter(routing.ModelConverter):
    model = Tester


@pytest.mark.usefixtures('clean_db')
class ObjectIdModelConverterTest:

    @pytest.fixture(autouse=True)
    def setup(self, app):
        app.url_map.converters['tester'] = TesterConverter

        @app.route('/model/<tester:model>')
        def model_tester(model):
            assert isinstance(model, Tester)
            return 'ok'

    def test_serialize_model_id_to_url(self):
        tester = Tester.objects.create()
        url = url_for('model_tester', model=tester)
        assert url == '/model/{0}'.format(str(tester.id))

    def test_serialize_model_slug_to_url(self):
        tester = Tester.objects.create(slug='slug')
        url = url_for('model_tester', model=tester)
        assert url == '/model/slug'

    def test_serialize_model_slug_with_unicode_to_url(self):
        tester = Tester.objects.create(slug='slüg')
        url = url_for('model_tester', model=tester)
        assert url == '/model/sl%C3%BCg'

    def test_serialize_object_id_to_url(self):
        id = ObjectId()
        url = url_for('model_tester', model=id)
        assert url == '/model/{0}'.format(str(id))

    def test_serialize_string_to_url(self):
        slug = 'slug'
        url = url_for('model_tester', model=slug)
        assert url == '/model/slug'

    def test_serialize_unicode_string_to_url(self):
        slug = 'slüg'
        url = url_for('model_tester', model=slug)
        assert url == '/model/sl%C3%BCg'

    def test_cant_serialize_model_to_url(self):
        tester = Tester()
        with pytest.raises(ValueError):
            url_for('model_tester', model=tester)

    def test_resolve_model_from_id(self, client):
        tester = Tester.objects.create(slug='slug')
        url = '/model/{0}'.format(str(tester.id))
        assert client.get(url).data == 'ok'

    def test_resolve_model_from_slug(self, client):
        Tester.objects.create(slug='slug')
        assert client.get('/model/slug').data == 'ok'

    def test_resolve_model_from_utf8_slug(self, client):
        Tester.objects.create(slug='slüg')
        assert client.get('/model/slüg').data == 'ok'

    def test_model_not_found(self, client):
        assert client.get('/model/not-found').status_code == 404
