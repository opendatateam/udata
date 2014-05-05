# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from shutil import rmtree
from StringIO import StringIO
from tempfile import mkdtemp

from flask import url_for

from udata.core import storages
from udata.core.storages.views import blueprint

from . import TestCase, WebTestMixin


class StorageTestCase(WebTestMixin, TestCase):
    def create_app(self):
        app = super(StorageTestCase, self).create_app()
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


class ResoucesStorageTest(StorageTestCase):
    def test_upload_resource(self):
        self.login()
        response = self.post(url_for('storage.add_resource'), {'file': (StringIO(b'aaa'), 'test.txt')})

        self.assert200(response)
        self.assertTrue(response.json['success'])
        self.assertIn('url', response.json)

    def test_upload_resource_bad_request(self):
        self.login()
        response = self.post(url_for('storage.add_resource'), {'bad': (StringIO(b'aaa'), 'test.txt')})

        self.assert400(response)
        self.assertFalse(response.json['success'])
        self.assertIn('error', response.json)


class ImagesStorageTest(StorageTestCase):
    pass


class AvatarsStorageTest(StorageTestCase):
    pass
