from io import BytesIO

import pytest
from flask import url_for
from PIL import Image

from udata.core import storages
from udata.core.user.factories import UserFactory
from udata.tests.api import PytestOnlyAPITestCase
from udata.tests.helpers import assert400, create_test_image

SVG = b'<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'


def gif() -> bytes:
    file = BytesIO()
    Image.new("RGB", size=(1, 1)).save(file, "gif")
    return file.getvalue()


def stored_file(url: str) -> str:
    """The name in the images storage of the file an uploaded image is served at."""
    return "content/" + url.rsplit("/content/", 1)[1]


class ContentImagesAPITest(PytestOnlyAPITestCase):
    def upload(self, content: bytes, name: str):
        return self.post(
            url_for("api.content_images"), {"file": (BytesIO(content), name)}, json=False
        )

    def test_upload_an_image(self):
        self.login(UserFactory())
        content = create_test_image().read()

        response = self.upload(content, "illustration.png")

        assert response.status_code == 201
        filename = stored_file(response.json["url"])
        assert filename.endswith(".png")
        assert storages.images.read(filename) == content

    def test_upload_a_vector_drawing(self):
        """Illustrations are often SVG, which Pillow does not read."""
        self.login(UserFactory())

        response = self.upload(SVG, "illustration.svg")

        assert response.status_code == 201
        filename = stored_file(response.json["url"])
        assert filename.endswith(".svg")
        assert storages.images.read(filename) == SVG

    def test_the_stored_extension_comes_from_the_content(self):
        """A file renamed `.png` stays what it is: an SVG served as a PNG would not display."""
        self.login(UserFactory())

        response = self.upload(SVG, "illustration.png")

        assert stored_file(response.json["url"]).endswith(".svg")

    @pytest.mark.parametrize(
        "content",
        [
            pytest.param(b"not an image", id="text"),
            pytest.param(b"<html><body>Hello</body></html>", id="xml-but-not-svg"),
            pytest.param(gif(), id="unsupported-format"),
        ],
    )
    def test_reject_what_is_not_an_image(self, content):
        self.login(UserFactory())

        assert400(self.upload(content, "illustration.png"))

    def test_upload_requires_a_user(self):
        response = self.upload(SVG, "illustration.svg")

        assert response.status_code == 401
