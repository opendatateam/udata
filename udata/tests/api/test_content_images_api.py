from io import BytesIO

import pytest
from flask import url_for
from PIL import Image

from udata.core import storages
from udata.core.storages.api import CONTENT_IMAGE_MAX_SIZE
from udata.core.user.factories import UserFactory
from udata.tests.api import PytestOnlyAPITestCase
from udata.tests.helpers import assert400, requires_s3_service

SVG = b'<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'


def encoded(image_format: str, size=(1, 1)) -> bytes:
    file = BytesIO()
    if image_format == "MPO":
        # A JPEG holding several pictures, as phone cameras write them
        frames = [Image.new("RGB", size, color) for color in ("red", "blue")]
        frames[0].save(file, "MPO", save_all=True, append_images=frames[1:])
    else:
        Image.new("RGB", size).save(file, image_format)
    return file.getvalue()


def stored_file(url: str) -> str:
    """The name in the images storage of the file an uploaded image is served at."""
    return "content/" + url.rsplit("/content/", 1)[1]


class ContentImagesAPITest(PytestOnlyAPITestCase):
    def upload(self, content: bytes, name: str):
        return self.post(
            url_for("api.content_images"), {"file": (BytesIO(content), name)}, json=False
        )

    @pytest.mark.parametrize(
        "image_format,extension",
        [("PNG", "png"), ("WEBP", "webp"), ("JPEG", "jpeg"), ("MPO", "jpeg")],
    )
    def test_upload_an_image(self, image_format, extension):
        self.login(UserFactory())
        content = encoded(image_format)

        response = self.upload(content, "illustration")

        assert response.status_code == 201
        filename = stored_file(response.json["url"])
        assert filename.endswith(f".{extension}")
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
            pytest.param(encoded("GIF"), id="unsupported-format"),
        ],
    )
    def test_reject_what_is_not_an_image(self, content):
        self.login(UserFactory())

        response = self.upload(content, "illustration.png")

        assert400(response)
        assert response.json["message"] == "Unsupported image format"

    def test_reject_a_file_too_large(self):
        """Refused before being read: decoding costs memory with the size of the file."""
        self.login(UserFactory())

        response = self.upload(b" " * (CONTENT_IMAGE_MAX_SIZE + 1) + SVG, "illustration.svg")

        assert400(response)
        assert response.json["message"] == "Image is too large"

    def test_reject_an_image_too_large_to_decode(self, monkeypatch):
        """Its header announces more pixels than Pillow accepts to decode."""
        monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1)
        self.login(UserFactory())

        response = self.upload(encoded("PNG", size=(2, 2)), "illustration.png")

        assert400(response)
        assert response.json["message"] == "Image is too large"

    def test_upload_requires_a_user(self):
        response = self.upload(SVG, "illustration.svg")

        assert response.status_code == 401


@requires_s3_service
@pytest.mark.usefixtures("s3_storages")
class ContentImagesS3Test(PytestOnlyAPITestCase):
    def test_a_vector_drawing_is_downloaded_rather_than_displayed(self):
        """Opened on its own, an SVG would run the scripts it holds: S3 serves it as an
        attachment, which an `<img>` still displays."""
        self.login(UserFactory())

        response = self.post(
            url_for("api.content_images"),
            {"file": (BytesIO(SVG), "illustration.svg")},
            json=False,
        )

        backend = storages.images.backend
        stored = backend.client.head_object(
            Bucket=backend.bucket.name,
            Key=storages.images._prefixed(stored_file(response.json["url"])),
        )
        assert stored["ContentType"] == "image/svg+xml"
        assert stored["ContentDisposition"] == "attachment"
