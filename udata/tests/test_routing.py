from uuid import uuid4

import pytest
from bson import ObjectId
from flask import url_for

from udata import routing
from udata.core.spatial.factories import GeoZoneFactory
from udata.core.spatial.models import GeoZone
from udata.mongo import db
from udata.mongo.slug_fields import SlugFollow
from udata.tests.helpers import assert200, assert404, assert_redirects


class UUIDConverterTest:
    @pytest.fixture(autouse=True)
    def setup(self, app):
        @app.route("/uuid/<uuid:uuid>")
        def uuid_tester(uuid):
            return "ok"

    def test_serialize_uuid_to_url(self):
        uuid = uuid4()
        url = url_for("uuid_tester", uuid=uuid)
        assert url == "/uuid/{0}".format(str(uuid))

    def test_serialize_string_uuid_to_url(self):
        uuid = uuid4()
        url = url_for("uuid_tester", uuid=str(uuid))
        assert url == "/uuid/{0}".format(str(uuid))

    def test_resolve_uuid(self, client):
        uuid = uuid4()
        url = "/uuid/{0}".format(str(uuid))
        assert200(client.get(url))

    def test_resolve_uuid_with_spaces(self, client):
        uuid = uuid4()
        url = "/uuid/{0} ".format(str(uuid))
        assert200(client.get(url))

    def test_bad_uuid_is_404(self, client):
        assert404(client.get("/uuid/bad"))


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


@pytest.mark.usefixtures("clean_db")
class ModelConverterMixin:
    @pytest.fixture(autouse=True)
    def setup(self, app):
        app.url_map.converters["tester"] = self.converter

        @app.route("/model/<tester:model>")
        def model_tester(model):
            assert isinstance(model, self.model)
            return str(model.id)

    def test_serialize_model_id_to_url(self):
        tester = self.model.objects.create()
        url = url_for("model_tester", model=tester)
        assert url == "/model/{0}".format(str(tester.id))

    def test_serialize_model_slug_to_url(self):
        tester = self.model.objects.create(slug="slug")
        url = url_for("model_tester", model=tester)
        assert url == "/model/slug"

    def test_serialize_object_id_to_url(self):
        id = ObjectId()
        url = url_for("model_tester", model=id)
        assert url == "/model/{0}".format(str(id))

    def test_serialize_string_to_url(self):
        slug = "slug"
        url = url_for("model_tester", model=slug)
        assert url == "/model/slug"

    def test_cant_serialize_model_to_url(self):
        tester = self.model()
        with pytest.raises(ValueError):
            url_for("model_tester", model=tester)

    def test_resolve_model_from_id(self, client):
        tester = self.model.objects.create(slug="slug")
        url = "/model/{0}".format(str(tester.id))
        assert200(client.get(url))

    def test_resolve_model_from_slug(self, client):
        self.model.objects.create(slug="slug")
        assert200(client.get("/model/slug"))

    def test_model_not_found(self, client):
        assert404(client.get("/model/not-found"))


class SlugAsStringFieldTest(ModelConverterMixin):
    model = Tester
    converter = TesterConverter

    def test_quote_model_slug_with_unicode_to_url(self):
        tester = Tester.objects.create(slug="slüg")
        url = url_for("model_tester", model=tester)
        assert url == "/model/sl%C3%BCg"

    def test_quote_unicode_string_to_url(self):
        slug = "slüg"
        url = url_for("model_tester", model=slug)
        assert url == "/model/sl%C3%BCg"

    def test_match_utf8_slug(self, client):
        slug = "slüg"
        Tester.objects.create(slug=slug)
        assert200(client.get("/model/slüg"))

    def test_match_normalized_utf8_slug(self, client):
        slug = "slüg"
        Tester.objects.create(slug=slug)
        assert200(client.get("/model/sl%C3%BCg"))


class AsSlugMixin(ModelConverterMixin):
    def test_serialize_model_slug_with_unicode_to_url(self):
        tester = self.model.objects.create(slug="slüg")
        url = url_for("model_tester", model=tester)
        assert url == "/model/slug"

    def test_serialize_unicode_string_to_url(self):
        slug = "slüg"
        url = url_for("model_tester", model=slug)
        assert url == "/model/slug"

    def test_redirect_to_normalized_utf8_slug(self, client):
        slug = "slüg"
        url = url_for("model_tester", model=slug)
        self.model.objects.create(slug=slug)
        assert_redirects(client.get("/model/slüg"), url)


class SlugAndIdTest(AsSlugMixin):
    model = SlugTester
    converter = SlugTesterConverter

    def test_url_hijack(self, client):
        """Tests for url hijack. If a object is created with"""
        """an existing object's id as it's slug,"""
        """the endpoint should return the first one"""
        tester = self.model.objects.create(slug="test_slug")
        tester2 = self.model.objects.create(slug=str(tester.id))
        model_url = url_for("model_tester", model=tester2)
        model_id = client.get(model_url)
        assert model_id.get_data() != str(tester2.id)


class SlugAsSlugFieldTest(AsSlugMixin):
    model = SlugTester
    converter = SlugTesterConverter

    def test_renaming(self, client):
        tester = self.model.objects.create(slug="old")
        old_url = url_for("model_tester", model=tester)
        assert200(client.get(old_url))

        tester.slug = "new"
        tester.save()
        new_url = url_for("model_tester", model=tester)
        assert200(client.get(new_url))
        assert404(client.get(old_url))


class SlugAsSLugFieldWithFollowTest(AsSlugMixin):
    model = RedirectTester
    converter = RedirectTesterConverter

    def test_renaming_redirect(self, client):
        tester = self.model.objects.create(slug="old")
        old_url = url_for("model_tester", model=tester)
        assert200(client.get(old_url))

        tester.slug = "new"
        tester.save().reload()

        new_url = url_for("model_tester", model=tester)
        assert200(client.get(new_url))
        assert_redirects(client.get(old_url), new_url)

    def test_multiple_renaming_redirect(self, client):
        tester = self.model.objects.create(slug="first")
        first_url = url_for("model_tester", model=tester)

        tester.slug = "second"
        tester.save().reload()
        second_url = url_for("model_tester", model=tester)
        assert200(client.get(second_url))
        assert_redirects(client.get(first_url), second_url)

        tester.slug = "last"
        tester.save().reload()
        last_url = url_for("model_tester", model=tester)
        assert200(client.get(last_url))
        assert_redirects(client.get(first_url), last_url)
        assert_redirects(client.get(second_url), last_url)

    def test_last_slug_has_priority(self, client):
        tester = self.model.objects.create(slug="first")
        first_url = url_for("model_tester", model=tester)

        tester.slug = "second"
        tester.save().reload()
        second_url = url_for("model_tester", model=tester)

        tester.slug = "third"
        tester.save().reload()
        third_url = url_for("model_tester", model=tester)

        new_tester = self.model.objects.create(slug="second")
        # Second slug should not be redirected anymore
        assert200(client.get(second_url))

        new_tester.slug = "last"
        new_tester.save().reload()
        last_url = url_for("model_tester", model=new_tester)

        # Current state should be:
        # - first redirects to third (tester)
        # - second redirects to last (new tester)
        # - third display tester
        # - last display new tester

        # Display or redirect to new_tester
        assert200(client.get(last_url))
        assert_redirects(client.get(second_url), last_url)
        # Display or redirect to tester
        assert200(client.get(third_url))
        assert_redirects(client.get(first_url), third_url)

    def test_redirects_destroyed_on_object_deleted(self, client):
        tester = self.model.objects.create(slug="first")
        first_url = url_for("model_tester", model=tester)

        tester.slug = "second"
        tester.save().reload()
        second_url = url_for("model_tester", model=tester)

        tester.slug = "last"
        tester.save().reload()
        last_url = url_for("model_tester", model=tester)

        tester.delete()
        assert404(client.get(first_url))
        assert404(client.get(second_url))
        assert404(client.get(last_url))

        assert SlugFollow.objects.count() == 0


@pytest.mark.usefixtures("clean_db")
@pytest.mark.options(TERRITORY_DEFAULT_PREFIX="fr")  # Not implemented
class TerritoryConverterTest:
    @pytest.fixture(autouse=True)
    def setup(self, app):
        @app.route("/territory/<territory:territory>")
        def territory_tester(territory):
            assert isinstance(territory, GeoZone)
            return territory.id

    def test_serialize_zone_with_validity(self):
        zone = GeoZoneFactory()
        url = url_for("territory_tester", territory=zone)
        expected = "/territory/{level}/{code}/{slug}"
        assert url == expected.format(**zone._data)

    def test_resolve_zone_without_optional_slug(self, client):
        zone = GeoZoneFactory()
        url = "/territory/{level}/{code}/"
        response = client.get(url.format(**zone._data))
        assert200(response)

    def test_resolve_zone_without_slug_nor_trailing_slash(self, client):
        zone = GeoZoneFactory()
        url = "/territory/{level}/{code}"
        response = client.get(url.format(**zone._data))
        assert200(response)

    def test_model_not_found(self, client):
        assert404(client.get("/territory/l/c"))
