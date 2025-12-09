from flask import url_for

from udata.tests.api import PytestOnlyAPITestCase
from udata.tests.helpers import assert200
from udata.utils import faker


def assert_stream_equal(response1, response2):
    __tracebackhide__ = True
    stream1 = list(response1.iter_encoded())
    stream2 = list(response2.iter_encoded())
    assert stream1 == stream2


class InternalBackendTest(PytestOnlyAPITestCase):
    def test_base_rendering(self):
        response = self.get(url_for("api.avatar", identifier=faker.word(), size=32))

        assert200(response)
        assert response.mimetype == "image/png"
        assert response.is_streamed
        etag, weak = response.get_etag()
        assert etag is not None

    def test_render_twice_the_same(self):
        identifier = faker.word()
        stream_a = self.get(url_for("api.avatar", identifier=identifier, size=32))
        stream_b = self.get(url_for("api.avatar", identifier=identifier, size=32))

        assert_stream_equal(stream_a, stream_b)
