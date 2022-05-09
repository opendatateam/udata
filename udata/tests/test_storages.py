import pytest

from datetime import datetime, timedelta
from io import BytesIO
from uuid import uuid4

from flask import url_for, json

from udata.core import storages
from udata.core.storages import utils
from udata.core.storages.api import chunk_filename, META
from udata.core.storages.tasks import purge_chunks
from udata.utils import faker

from .helpers import assert200, assert400

from os.path import basename

from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request


class StorageUtilsTest:
    '''
    Perform all tests on a file of size 2 * CHUNCK_SIZE = 2 * (2 ** 16).
    Expected values are precomputed with shell `md5sum`, `sha1sum`...
    '''
    @pytest.fixture(autouse=True)
    def write_file(self, tmpdir):
        tmpfile = tmpdir.join('test.txt')
        tmpfile.write_binary(b'a' * 2 * (2 ** 16))
        self.file = self.filestorage(str(tmpfile))

    def filestorage(self, filename):
        data = open(filename, 'rb')
        builder = EnvironBuilder(method='POST', data={
            'file': (data, basename(filename))
        })
        env = builder.get_environ()
        req = Request(env)
        return req.files['file']

    def test_sha1(self):
        # Output of sha1sum
        expected = 'ce5653590804baa9369f72d483ed9eba72f04d29'
        assert utils.sha1(self.file) == expected

    def test_md5(self):
        expected = '81615449a98aaaad8dc179b3bec87f38'  # Output of md5sum
        assert utils.md5(self.file) == expected

    def test_crc32(self):
        expected = 'CA975130'  # Output of cksfv
        assert utils.crc32(self.file) == expected

    def test_mime(self):
        assert utils.mime('test.txt') == 'text/plain'
        assert utils.mime('test') is None

    def test_extension_default(self, app):
        assert utils.extension('test.txt') == 'txt'
        assert utils.extension('prefix/test.txt') == 'txt'
        assert utils.extension('prefix.with.dot/test.txt') == 'txt'

    def test_extension_compound(self, app):
        assert utils.extension('test.tar.gz') == 'tar.gz'
        assert utils.extension('prefix.with.dot/test.tar.gz') == 'tar.gz'

    def test_extension_compound_with_allowed_extension(self, app):
        assert utils.extension('test.2022.csv.tar.gz') == 'csv.tar.gz'
        assert utils.extension('prefix.with.dot/test.2022.csv.tar.gz') == 'csv.tar.gz'

    def test_extension_compound_without_allowed_extension(self, app):
        assert utils.extension('test.2022.tar.gz') == 'tar.gz'
        assert utils.extension('prefix.with.dot/test.2022.tar.gz') == 'tar.gz'

    def test_no_extension(self, app):
        assert utils.extension('test') is None
        assert utils.extension('prefix/test') is None

    def test_normalize_no_changes(self):
        assert utils.normalize('test.txt') == 'test.txt'

    def test_normalize_spaces(self):
        expected = 'test-with-spaces.txt'
        assert utils.normalize('test with  spaces.txt') == expected

    def test_normalize_to_lower(self):
        assert utils.normalize('Test.TXT') == 'test.txt'

    def test_normalize_special_chars(self):
        assert utils.normalize('éàü@€.txt') == 'eau-eur.txt'


@pytest.mark.usefixtures('app')
class ConfigurableAllowedExtensionsTest:
    def test_has_default(self):
        assert 'csv' in storages.CONFIGURABLE_AUTHORIZED_TYPES
        assert 'xml' in storages.CONFIGURABLE_AUTHORIZED_TYPES
        assert 'json' in storages.CONFIGURABLE_AUTHORIZED_TYPES
        assert 'exe' not in storages.CONFIGURABLE_AUTHORIZED_TYPES
        assert 'bat' not in storages.CONFIGURABLE_AUTHORIZED_TYPES

    @pytest.mark.options(ALLOWED_RESOURCES_EXTENSIONS=['csv', 'json'])
    def test_with_config(self):
        assert 'csv' in storages.CONFIGURABLE_AUTHORIZED_TYPES
        assert 'json' in storages.CONFIGURABLE_AUTHORIZED_TYPES
        assert 'xml' not in storages.CONFIGURABLE_AUTHORIZED_TYPES
        assert 'exe' not in storages.CONFIGURABLE_AUTHORIZED_TYPES
        assert 'bat' not in storages.CONFIGURABLE_AUTHORIZED_TYPES


@pytest.mark.usefixtures('instance_path')
class StorageUploadViewTest:
    def test_standard_upload(self, client):
        client.login()
        response = client.post(
            url_for('storage.upload', name='resources'),
            {'file': (BytesIO(b'aaa'), 'Test with  spaces.TXT')})

        assert200(response)
        assert response.json['success']
        assert 'url' in response.json
        assert 'size' in response.json
        assert 'sha1' in response.json
        assert 'filename' in response.json
        filename = response.json['filename']
        assert filename.endswith('test-with-spaces.txt')
        expected = storages.resources.url(filename, external=True)
        assert response.json['url'] == expected
        assert response.json['mime'] == 'text/plain'

    def test_chunked_upload(self, client):
        client.login()
        url = url_for('storage.upload', name='tmp')
        uuid = str(uuid4())
        parts = 4

        for i in range(parts):
            response = client.post(url, {
                'file': (BytesIO(b'a'), 'blob'),
                'uuid': uuid,
                'filename': 'Test with  spaces.TXT',
                'partindex': i,
                'partbyteoffset': 0,
                'totalfilesize': parts,
                'totalparts': parts,
                'chunksize': 1,
            })

            assert200(response)
            assert response.json['success']
            assert 'filename' not in response.json
            assert 'url' not in response.json
            assert 'size' not in response.json
            assert 'sha1' not in response.json
            assert 'url' not in response.json

        response = client.post(url, {
            'uuid': uuid,
            'filename': 'Test with  spaces.TXT',
            'totalfilesize': parts,
            'totalparts': parts,
        })
        assert 'filename' in response.json
        assert 'url' in response.json
        assert 'size' in response.json
        assert response.json['size'] == parts
        assert 'sha1' in response.json
        expected_filename = 'test-with-spaces.txt'
        filename = response.json['filename']
        assert filename.endswith(expected_filename)
        expected_url = storages.tmp.url(filename, external=True)
        assert response.json['url'] == expected_url
        assert response.json['mime'] == 'text/plain'
        assert storages.tmp.read(filename) == b'aaaa'
        assert list(storages.chunks.list_files()) == []

    def test_chunked_upload_bad_chunk(self, client):
        client.login()
        url = url_for('storage.upload', name='tmp')
        uuid = str(uuid4())
        parts = 4

        response = client.post(url, {
            'file': (BytesIO(b'a'), 'blob'),
            'uuid': uuid,
            'filename': 'test.txt',
            'partindex': 0,
            'partbyteoffset': 0,
            'totalfilesize': parts,
            'totalparts': parts,
            'chunksize': 10,  # Does not match
        })

        assert400(response)
        assert not response.json['success']
        assert 'filename' not in response.json
        assert 'url' not in response.json
        assert 'size' not in response.json
        assert 'sha1' not in response.json
        assert 'url' not in response.json

        assert list(storages.chunks.list_files()) == []

    def test_upload_resource_bad_request(self, client):
        client.login()
        response = client.post(
            url_for('storage.upload', name='tmp'),
            {'bad': (BytesIO(b'aaa'), 'test.txt')})

        assert400(response)
        assert not response.json['success']
        assert 'error' in response.json


@pytest.mark.usefixtures('instance_path')
class ChunksRetentionTest:
    def create_chunks(self, uuid, nb=3, last=None):
        for i in range(nb):
            storages.chunks.write(chunk_filename(uuid, i), faker.word())
        storages.chunks.write(chunk_filename(uuid, META), json.dumps({
            'uuid': str(uuid),
            'filename': faker.file_name(),
            'totalparts': nb + 1,
            'lastchunk': last or datetime.now(),
        }))

    @pytest.mark.options(UPLOAD_MAX_RETENTION=0)
    def test_chunks_cleanup_after_max_retention(self, client):
        uuid = str(uuid4())
        self.create_chunks(uuid)
        purge_chunks.apply()
        assert list(storages.chunks.list_files()) == []
        assert not storages.chunks.exists(uuid)  # Directory should be removed too

    @pytest.mark.options(UPLOAD_MAX_RETENTION=60 * 60)  # 1 hour
    def test_chunks_kept_before_max_retention(self, client):
        not_expired = datetime.now()
        expired = datetime.now() - timedelta(hours=2)
        expired_uuid = str(uuid4())
        active_uuid = str(uuid4())
        parts = 3
        self.create_chunks(expired_uuid, nb=parts, last=expired)
        self.create_chunks(active_uuid, nb=parts, last=not_expired)
        purge_chunks.apply()
        expected = set([
            chunk_filename(active_uuid, i) for i in range(parts)
        ])
        expected.add(chunk_filename(active_uuid, META))
        assert set(storages.chunks.list_files()) == expected
        assert not storages.chunks.exists(expired_uuid)  # Directory should be removed too
