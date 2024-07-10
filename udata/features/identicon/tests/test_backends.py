import pytest

from udata.features.identicon.backends import internal
from udata.tests.helpers import assert200
from udata.utils import faker

pytestmark = pytest.mark.usefixtures("app")


def assert_stream_equal(response1, response2):
    __tracebackhide__ = True
    stream1 = list(response1.iter_encoded())
    stream2 = list(response2.iter_encoded())
    assert stream1 == stream2


class InternalBackendTest:
    def test_base_rendering(self):
        response = internal(faker.word(), 32)
        assert200(response)
        assert response.mimetype == "image/png"
        assert response.is_streamed
        etag, weak = response.get_etag()
        assert etag is not None

    def test_render_twice_the_same(self):
        identifier = faker.word()
        assert_stream_equal(internal(identifier, 32), internal(identifier, 32))
