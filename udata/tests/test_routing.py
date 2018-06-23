# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from bson import ObjectId
from uuid import uuid4

from flask import url_for

from udata import routing
from udata.core.spatial.models import GeoZone
from udata.core.spatial.factories import GeoZoneFactory
from udata.models import db
from udata.tests.helpers import assert200, assert_redirects


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
        assert client.get(url).data == b'ok'

    def test_resolve_uuid_with_spaces(self, client):
        uuid = uuid4()
        url = '/uuid/{0} '.format(str(uuid))
        assert client.get(url).data == b'ok'

    def test_bad_uuid_is_404(self, client):
        assert client.get('/uuid/bad').status_code == 404


class Tester(db.Document):
    slug = db.StringField()


class SlugTester(db.Document):
    slug = db.SlugField()


class RedirectTester(db.Document):
    slug = db.SlugField(follow=True)


class TesterConverter(routing.ModelConverter):
    model = Tester


class SlugTesterConverter(routing.ModelConverter):
    model = SlugTester


class RedirectTesterConverter(routing.ModelConverter):
    model = RedirectTester


@pytest.mark.usefixtures('clean_db')
class ModelConverterMixin:
    @pytest.fixture(autouse=True)
    def setup(self, app):
        app.url_map.converters['tester'] = self.converter

        @app.route('/model/<tester:model>')
        def model_tester(model):
            assert isinstance(model, self.model)
            return 'ok'

    def test_serialize_model_id_to_url(self):
        tester = self.model.objects.create()
        url = url_for('model_tester', model=tester)
        assert url == '/model/{0}'.format(str(tester.id))

    def test_serialize_model_slug_to_url(self):
        tester = self.model.objects.create(slug='slug')
        url = url_for('model_tester', model=tester)
        assert url == '/model/slug'

    def test_serialize_object_id_to_url(self):
        id = ObjectId()
        url = url_for('model_tester', model=id)
        assert url == '/model/{0}'.format(str(id))

    def test_serialize_string_to_url(self):
        slug = 'slug'
        url = url_for('model_tester', model=slug)
        assert url == '/model/slug'

    def test_cant_serialize_model_to_url(self):
        tester = self.model()
        with pytest.raises(ValueError):
            url_for('model_tester', model=tester)

    def test_resolve_model_from_id(self, client):
        tester = self.model.objects.create(slug='slug')
        url = '/model/{0}'.format(str(tester.id))
        assert client.get(url).data == b'ok'

    def test_resolve_model_from_slug(self, client):
        self.model.objects.create(slug='slug')
        assert client.get('/model/slug').data == b'ok'

    def test_model_not_found(self, client):
        assert client.get('/model/not-found').status_code == 404


class SlugAsStringFieldTest(ModelConverterMixin):
    model = Tester
    converter = TesterConverter

    def test_quote_model_slug_with_unicode_to_url(self):
        tester = Tester.objects.create(slug='slüg')
        url = url_for('model_tester', model=tester)
        assert url == '/model/sl%C3%BCg'

    def test_quote_unicode_string_to_url(self):
        slug = 'slüg'
        url = url_for('model_tester', model=slug)
        assert url == '/model/sl%C3%BCg'

    def test_match_utf8_slug(self, client):
        slug = 'slüg'
        Tester.objects.create(slug=slug)
        assert200(client.get('/model/slüg'))

    def test_match_normalized_utf8_slug(self, client):
        slug = 'slüg'
        Tester.objects.create(slug=slug)
        assert200(client.get('/model/sl%C3%BCg'))


class AsSlugMixin(ModelConverterMixin):
    def test_serialize_model_slug_with_unicode_to_url(self):
        tester = self.model.objects.create(slug='slüg')
        url = url_for('model_tester', model=tester)
        assert url == '/model/slug'

    def test_serialize_unicode_string_to_url(self):
        slug = 'slüg'
        url = url_for('model_tester', model=slug)
        assert url == '/model/slug'

    def test_redirect_to_normalized_utf8_slug(self, client):
        slug = 'slüg'
        url = url_for('model_tester', model=slug)
        self.model.objects.create(slug=slug)
        assert_redirects(client.get('/model/slüg'), url)


class SlugAsSlugFieldTest(AsSlugMixin):
    model = SlugTester
    converter = SlugTesterConverter


class SlugAsSLugFieldWithFollowTest(AsSlugMixin):
    model = RedirectTester
    converter = RedirectTesterConverter


@pytest.mark.usefixtures('clean_db')
@pytest.mark.options(TERRITORY_DEFAULT_PREFIX='fr')  # Not implemented
class TerritoryConverterTest:

    @pytest.fixture(autouse=True)
    def setup(self, app):

        @app.route('/territory/<territory:territory>')
        def territory_tester(territory):
            assert isinstance(territory, GeoZone)
            return 'ok'

    def test_serialize_zone_with_validity(self):
        zone = GeoZoneFactory()
        url = url_for('territory_tester', territory=zone)
        expected = '/territory/{level}/{code}@{validity.start}/{slug}'
        assert url == expected.format(**zone._data)

    def test_serialize_zone_without_validity(self):
        zone = GeoZoneFactory(validity=None)
        url = url_for('territory_tester', territory=zone)
        expected = '/territory/{level}/{code}@latest/{slug}'
        assert url == expected.format(**zone._data)

    def test_serialize_default_prefix_zone_with_validity(self):
        zone = GeoZoneFactory(level='fr:level')
        url = url_for('territory_tester', territory=zone)
        expected = '/territory/level/{code}@{validity.start}/{slug}'
        assert url == expected.format(**zone._data)

    def test_serialize_default_prefix_zone_without_validity(self):
        zone = GeoZoneFactory(level='fr:level', validity=None)
        url = url_for('territory_tester', territory=zone)
        expected = '/territory/level/{code}@latest/{slug}'
        assert url == expected.format(**zone._data)

    def test_resolve_default_prefix_zone_with_validity(self, client):
        zone = GeoZoneFactory(level='fr:level')
        url = '/territory/level/{code}@{validity.start}/{slug}'
        response = client.get(url.format(**zone._data))
        assert200(response)

    def test_resolve_default_prefix_zone_without_validity(self, client):
        zone = GeoZoneFactory(level='fr:level', validity=None)
        url = '/territory/level/{code}@latest/{slug}'
        response = client.get(url.format(**zone._data))
        assert200(response)

    def test_resolve_zone_with_validity(self, client):
        zone = GeoZoneFactory()
        url = '/territory/{level}/{code}@{validity.start}/{slug}'
        response = client.get(url.format(**zone._data))
        assert200(response)

    def test_resolve_zone_with_latest_validity(self, client):
        zone = GeoZoneFactory(validity=None)
        url = '/territory/{level}/{code}@latest/{slug}'
        response = client.get(url.format(**zone._data))
        assert200(response)

    def test_resolve_zone_without_validity(self, client):
        zone = GeoZoneFactory(validity=None)
        url = '/territory/{level}/{code}/{slug}'
        response = client.get(url.format(**zone._data))
        assert200(response)

    def test_resolve_zone_without_optionnal_slug(self, client):
        zone = GeoZoneFactory(validity=None)
        url = '/territory/{level}/{code}@latest/'
        response = client.get(url.format(**zone._data))
        assert200(response)

    def test_resolve_zone_without_slug_nor_trailing_slash(self, client):
        zone = GeoZoneFactory(validity=None)
        url = '/territory/{level}/{code}@latest'
        response = client.get(url.format(**zone._data))
        assert200(response)

    def test_model_not_found(self, client):
        assert client.get('/territory/l/c@latest').status_code == 404

