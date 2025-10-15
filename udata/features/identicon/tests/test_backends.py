from udata.features.identicon.backends import internal
from udata.tests.api import PytestOnlyAPITestCase
from udata.tests.helpers import assert200
from udata.utils import faker


class InternalBackendTest(PytestOnlyAPITestCase):
    def test_base_rendering(self):
        response = internal(faker.word(), 32)
        assert200(response)
        assert response.mimetype == "image/png"
        assert response.is_streamed
        etag, weak = response.get_etag()
        assert etag is not None

    def test_render_twice_the_same(self):
        identifier = faker.word()
        self.assertStreamEqual(internal(identifier, 32), internal(identifier, 32))
