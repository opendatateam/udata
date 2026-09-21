import hashlib
import io
from datetime import UTC, datetime, timedelta
from os.path import basename
from uuid import uuid4

import pytest
from flask import json
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from udata.core import storages
from udata.core.storages import utils
from udata.core.storages.api import META, ChunksReader, chunk_filename
from udata.core.storages.tasks import purge_chunks
from udata.tests import PytestOnlyTestCase
from udata.utils import faker


class StorageUtilsTest(PytestOnlyTestCase):
    """
    Perform all tests on a file of size 2 * CHUNCK_SIZE = 2 * (2 ** 16).
    Expected values are precomputed with shell `md5sum`, `sha1sum`...
    """

    @pytest.fixture(autouse=True)
    def write_file(self, tmpdir):
        tmpfile = tmpdir.join("test.txt")
        tmpfile.write_binary(b"a" * 2 * (2**16))
        self.file = self.filestorage(str(tmpfile))

    def filestorage(self, filename):
        data = open(filename, "rb")
        builder = EnvironBuilder(method="POST", data={"file": (data, basename(filename))})
        env = builder.get_environ()
        req = Request(env)
        return req.files["file"]

    def test_sha1(self):
        # Output of sha1sum
        expected = "ce5653590804baa9369f72d483ed9eba72f04d29"
        assert utils.sha1(self.file) == expected

    def test_md5(self):
        expected = "81615449a98aaaad8dc179b3bec87f38"  # Output of md5sum
        assert utils.md5(self.file) == expected

    def test_crc32(self):
        expected = "CA975130"  # Output of cksfv
        assert utils.crc32(self.file) == expected

    def test_mime(self):
        assert utils.mime("test.txt") == "text/plain"
        assert utils.mime("test") is None

    def test_extension_default(self, app):
        assert utils.extension("test.txt") == "txt"
        assert utils.extension("prefix/test.txt") == "txt"
        assert utils.extension("prefix.with.dot/test.txt") == "txt"

    def test_extension_compound(self, app):
        assert utils.extension("test.tar.gz") == "tar.gz"
        assert utils.extension("prefix.with.dot/test.tar.gz") == "tar.gz"

    def test_extension_compound_with_allowed_extension(self, app):
        assert utils.extension("test.2022.csv.tar.gz") == "csv.tar.gz"
        assert utils.extension("prefix.with.dot/test.2022.csv.tar.gz") == "csv.tar.gz"

    def test_extension_compound_without_allowed_extension(self, app):
        assert utils.extension("test.2022.tar.gz") == "tar.gz"
        assert utils.extension("prefix.with.dot/test.2022.tar.gz") == "tar.gz"

    def test_no_extension(self, app):
        assert utils.extension("test") is None
        assert utils.extension("prefix/test") is None

    def test_normalize_no_changes(self):
        assert utils.normalize("test.txt") == "test.txt"

    def test_normalize_spaces(self):
        expected = "test-with-spaces.txt"
        assert utils.normalize("test with  spaces.txt") == expected

    def test_normalize_to_lower(self):
        assert utils.normalize("Test.TXT") == "test.txt"

    def test_normalize_special_chars(self):
        assert utils.normalize("éàü@€.txt") == "eau-eur.txt"


class ConfigurableAllowedExtensionsTest(PytestOnlyTestCase):
    def test_has_default(self):
        assert "csv" in storages.CONFIGURABLE_AUTHORIZED_TYPES
        assert "xml" in storages.CONFIGURABLE_AUTHORIZED_TYPES
        assert "json" in storages.CONFIGURABLE_AUTHORIZED_TYPES
        assert "exe" not in storages.CONFIGURABLE_AUTHORIZED_TYPES
        assert "bat" not in storages.CONFIGURABLE_AUTHORIZED_TYPES

    @pytest.mark.options(ALLOWED_RESOURCES_EXTENSIONS=["csv", "json"])
    def test_with_config(self):
        assert "csv" in storages.CONFIGURABLE_AUTHORIZED_TYPES
        assert "json" in storages.CONFIGURABLE_AUTHORIZED_TYPES
        assert "xml" not in storages.CONFIGURABLE_AUTHORIZED_TYPES
        assert "exe" not in storages.CONFIGURABLE_AUTHORIZED_TYPES
        assert "bat" not in storages.CONFIGURABLE_AUTHORIZED_TYPES


@pytest.mark.usefixtures("instance_path")
class ChunksRetentionTest(PytestOnlyTestCase):
    def create_chunks(self, uuid, nb=3, last=None):
        for i in range(nb):
            storages.chunks.write(chunk_filename(uuid, i), faker.word())
        storages.chunks.write(
            chunk_filename(uuid, META),
            json.dumps(
                {
                    "uuid": str(uuid),
                    "filename": faker.file_name(),
                    "totalparts": nb + 1,
                    "lastchunk": last or datetime.now(UTC),
                }
            ),
        )

    @pytest.mark.options(UPLOAD_MAX_RETENTION=0)
    def test_chunks_cleanup_after_max_retention(self, client):
        uuid = str(uuid4())
        self.create_chunks(uuid)
        purge_chunks.apply()
        assert list(storages.chunks.list_files()) == []
        assert not storages.chunks.exists(uuid)  # Directory should be removed too

    @pytest.mark.options(UPLOAD_MAX_RETENTION=60 * 60)  # 1 hour
    def test_chunks_kept_before_max_retention(self, client):
        not_expired = datetime.now(UTC)
        expired = datetime.now(UTC) - timedelta(hours=2)
        expired_uuid = str(uuid4())
        active_uuid = str(uuid4())
        parts = 3
        self.create_chunks(expired_uuid, nb=parts, last=expired)
        self.create_chunks(active_uuid, nb=parts, last=not_expired)
        purge_chunks.apply()
        expected = set([chunk_filename(active_uuid, i) for i in range(parts)])
        expected.add(chunk_filename(active_uuid, META))
        assert set(storages.chunks.list_files()) == expected
        assert not storages.chunks.exists(expired_uuid)  # Directory should be removed too


class MeasuredStreamTest(PytestOnlyTestCase):
    """The wrapper a storage reads an upload through."""

    def test_digests_a_content_read_block_by_block(self):
        # A storage reads by blocks, so the digest and the size are accumulated
        # over several reads. A payload of a few bytes never takes that path.
        content = b"0123456789" * 5000
        stream = utils.MeasuredStream(io.BytesIO(content))

        read = b""
        while block := stream.read(4096):
            read += block

        assert read == content
        assert stream.size == len(content)
        assert stream.checksum == hashlib.sha1(content).hexdigest()

    def test_digests_a_content_read_in_one_go(self):
        content = b"0123456789" * 5000
        stream = utils.MeasuredStream(io.BytesIO(content))

        assert stream.read() == content
        assert stream.size == len(content)
        assert stream.checksum == hashlib.sha1(content).hexdigest()

    def test_digests_an_empty_stream(self):
        stream = utils.MeasuredStream(io.BytesIO(b""))

        assert stream.read() == b""
        assert stream.size == 0
        assert stream.checksum == hashlib.sha1(b"").hexdigest()


@pytest.mark.usefixtures("instance_path")
class ChunksReaderTest(PytestOnlyTestCase):
    """The stream a chunked upload is handed to its destination storage as."""

    def store_parts(self, uuid, parts):
        for index, part in enumerate(parts):
            storages.chunks.write(chunk_filename(uuid, index), part)

    def test_reads_every_part_in_order(self, client):
        uuid = str(uuid4())
        self.store_parts(uuid, [b"first", b"second", b"third"])

        stream = io.BufferedReader(ChunksReader(uuid, 3))

        assert stream.read() == b"firstsecondthird"

    def test_reads_parts_wider_than_the_read_buffer(self, client):
        # A part is megabytes wide in production while a read asks for a few
        # kilobytes at a time, so it is always handed over in several reads.
        # Parts of a single byte never take that path.
        uuid = str(uuid4())
        parts = [bytes([index]) * 10000 for index in range(1, 4)]
        self.store_parts(uuid, parts)

        stream = io.BufferedReader(ChunksReader(uuid, len(parts)), buffer_size=1024)

        assert stream.read() == b"".join(parts)

    def test_a_read_shorter_than_a_part_keeps_the_rest_for_the_next_one(self, client):
        uuid = str(uuid4())
        self.store_parts(uuid, [b"0123456789"])
        reader = ChunksReader(uuid, 1)
        target = bytearray(4)

        assert reader.readinto(target) == 4
        assert bytes(target) == b"0123"
        assert reader.readinto(target) == 4
        assert bytes(target) == b"4567"
        assert reader.readinto(target) == 2
        assert bytes(target[:2]) == b"89"
        assert reader.readinto(target) == 0
