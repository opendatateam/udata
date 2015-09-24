# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import tempfile

from shutil import rmtree
from StringIO import StringIO
from tempfile import mkdtemp

from flask import url_for

from udata.core import storages
from udata.core.storages import utils
from udata.core.storages.views import blueprint

from . import TestCase, WebTestMixin


from os.path import basename


from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request


class TestStorageUtils(TestCase):
    '''
    Perform all tests on a file of size 2 * CHUNCK_SIZE = 2 * (2 ** 16).
    Expected values are precomputed with shell `md5sum`, `sha1sum`...
    '''
    def setUp(self):
        _, self.filename = tempfile.mkstemp()
        with open(self.filename, 'wb') as out:
            out.write(b'a' * 2 * (2 ** 16))
        self.file = self.filestorage(self.filename)

    def filestorage(self, filename):
        data = open(filename)
        builder = EnvironBuilder(method='POST', data={
            'file': (data, basename(filename))
        })
        env = builder.get_environ()
        req = Request(env)
        return req.files['file']

    def tearDown(self):
        os.remove(self.filename)

    def test_sha1(self):
        # Output of sha1sum
        expected = 'ce5653590804baa9369f72d483ed9eba72f04d29'
        self.assertEqual(utils.sha1(self.file), expected)

    def test_md5(self):
        expected = '81615449a98aaaad8dc179b3bec87f38'  # Output of md5sum
        self.assertEqual(utils.md5(self.file), expected)

    def test_crc32(self):
        expected = 'CA975130'  # Output of cksfv
        self.assertEqual(utils.crc32(self.file), expected)

    def test_mime(self):
        self.assertEqual(utils.mime('test.txt'), 'text/plain')
        self.assertIsNone(utils.mime('test'))


class StorageTestMixin(object):
    def create_app(self):
        app = super(StorageTestMixin, self).create_app()
        self._instance_path = app.instance_path
        app.instance_path = mkdtemp()
        storages.init_app(app)
        app.register_blueprint(blueprint)
        return app

    def tearsDown(self):
        '''Cleanup the mess'''
        rmtree(self.app.instance_path)
        self.app.instance_path = self._instance_path
        super(StorageTestCase, self).tearsDown()


class StorageTestCase(StorageTestMixin, WebTestMixin, TestCase):
    pass


class StorageUploadViewTest(StorageTestCase):
    def test_upload(self):
        self.login()
        response = self.post(
            url_for('storage.upload', name='tmp'),
            {'file': (StringIO(b'aaa'), 'test.txt')})

        self.assert200(response)
        self.assertTrue(response.json['success'])
        self.assertIn('filename', response.json)
        self.assertIn('url', response.json)
        self.assertIn('mime', response.json)
        self.assertIn('size', response.json)
        self.assertIn('sha1', response.json)
        self.assertEqual(response.json['url'],
                         storages.tmp.url(response.json['filename'],
                                          external=True))
        self.assertEqual(response.json['mime'], 'text/plain')

    def test_upload_resource_bad_request(self):
        self.login()
        response = self.post(
            url_for('storage.upload', name='tmp'),
            {'bad': (StringIO(b'aaa'), 'test.txt')})

        self.assert400(response)
        self.assertFalse(response.json['success'])
        self.assertIn('error', response.json)
