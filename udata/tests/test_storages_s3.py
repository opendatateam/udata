from io import BytesIO
from uuid import uuid4

import pytest
from flask import url_for
from flask_storage.errors import UnauthorizedFileType

from udata.core import storages
from udata.core.dataset.factories import DatasetFactory
from udata.tests import PytestOnlyTestCase
from udata.tests.api import APITestCase
from udata.tests.helpers import requires_s3_service


@requires_s3_service
@pytest.mark.usefixtures("s3_storages")
class S3StorageContractTest(PytestOnlyTestCase):
    """The storage operations udata relies on, run against a real S3 service.

    Everything asserted here holds identically on the local backend: this is
    the contract the resources migration must not break.
    """

    def test_save_then_read(self):
        filename = storages.resources.save(BytesIO(b"content"), filename="test.txt")

        assert filename == "test.txt"
        assert storages.resources.read(filename) == b"content"
        assert storages.resources.exists(filename)

    def test_save_under_a_prefix(self):
        filename = storages.resources.save(
            BytesIO(b"content"), filename="test.txt", prefix="dataset/20260805-120000"
        )

        assert filename == "dataset/20260805-120000/test.txt"
        assert storages.resources.read(filename) == b"content"

    def test_save_rejects_an_unauthorized_extension(self):
        with pytest.raises(UnauthorizedFileType):
            storages.resources.save(BytesIO(b"content"), filename="test.exe")

    def test_delete(self):
        filename = storages.resources.save(BytesIO(b"content"), filename="test.txt")

        storages.resources.delete(filename)

        assert not storages.resources.exists(filename)

    def test_list_files(self):
        storages.resources.save(BytesIO(b"content"), filename="test.txt")
        storages.resources.save(BytesIO(b"content"), filename="nested/other.txt")

        assert set(storages.resources.list_files()) == {"test.txt", "nested/other.txt"}

    def test_url_points_at_the_stored_file(self):
        filename = storages.resources.save(BytesIO(b"content"), filename="test.txt")

        assert storages.resources.url(filename, external=True).endswith("test.txt")


@requires_s3_service
@pytest.mark.usefixtures("s3_storages")
class S3ResourceUploadTest(APITestCase):
    """The resource upload endpoint, backed by S3 rather than the filesystem."""

    def test_upload_stores_the_file(self):
        user = self.login()
        dataset = DatasetFactory(owner=user)

        response = self.post(
            url_for("api.upload_new_dataset_resource", dataset=dataset),
            {"file": (BytesIO(b"aaa"), "test.txt")},
            json=False,
        )

        self.assert201(response)
        dataset.reload()
        resource = dataset.resources[0]
        assert resource.fs_filename in storages.resources
        assert storages.resources.read(resource.fs_filename) == b"aaa"
        # Same values as on the local backend: metadata describes the upload,
        # not what the storage reports back.
        assert response.json["mime"] == "text/plain"
        assert response.json["checksum"] == {
            "type": "sha1",
            "value": "7e240de74fb1ed08fa08d38063f6a6a91462a815",
        }

    def test_chunked_upload_stores_the_combined_file(self):
        user = self.login()
        dataset = DatasetFactory(owner=user)
        url = url_for("api.upload_new_dataset_resource", dataset=dataset)
        uuid = str(uuid4())
        parts = [b"a", b"b", b"c", b"d"]

        for index, part in enumerate(parts):
            response = self.post(
                url,
                {
                    "file": (BytesIO(part), "blob"),
                    "uuid": uuid,
                    "filename": "test.txt",
                    "partindex": index,
                    "partbyteoffset": 0,
                    "totalparts": len(parts),
                    "chunksize": 1,
                },
                json=False,
            )
            self.assert200(response)

        response = self.post(
            url,
            {"uuid": uuid, "filename": "test.txt", "totalparts": len(parts)},
            json=False,
        )

        self.assert201(response)
        dataset.reload()
        resource = dataset.resources[0]
        assert storages.resources.read(resource.fs_filename) == b"abcd"
        assert list(storages.chunks.list_files()) == []
        assert response.json["mime"] == "text/plain"
        # The sha1 of b"abcd", digested while streaming the parts to S3
        assert response.json["checksum"] == {
            "type": "sha1",
            "value": "81fe8bfe87576c3ecb22426f8e57847382917acf",
        }
