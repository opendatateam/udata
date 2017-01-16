# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import shutil
import tempfile

from flask import url_for
import flask_fs as fs

from udata.models import db
from udata.forms import Form
from udata.forms.fields import ImageField
from udata.frontend.helpers import placeholder
from udata.tests import DBTestMixin, FSTestMixin, TestCase
from udata.core.storages import tmp
from udata.core.storages.views import blueprint

log = logging.getLogger(__name__)

SIZES = [16, 32]

storage = fs.Storage('test')


class PostData(dict):
    def getlist(self, key):
        value = self[key]
        if not isinstance(value, (list, tuple)):
            value = [value]
        return value


class ImageFieldTest(DBTestMixin, FSTestMixin, TestCase):
    class D(db.Document):
        image = db.ImageField(fs=storage)
        thumbnail = db.ImageField(fs=storage, thumbnails=SIZES)

    class F(Form):
        image = ImageField()
        thumbnail = ImageField(sizes=SIZES)

    def create_app(self):
        app = super(ImageFieldTest, self).create_app()
        self._instance_path = app.instance_path
        app.instance_path = tempfile.mkdtemp()
        fs.init_app(app, storage, tmp)
        app.register_blueprint(blueprint)
        return app

    def tearsDown(self):
        '''Cleanup the mess'''
        shutil.rmtree(self.app.instance_path)
        self.app.instance_path = self._instance_path
        super(ImageFieldTest, self).tearsDown()

    def test_empty(self):
        form = self.F()
        endpoint = url_for('storage.upload', name=tmp.name)
        self.assertEqual(form.image.filename.data, None)
        self.assertEqual(form.image.bbox.data, None)

        self.assertEqual(form.thumbnail.filename.data, None)
        self.assertEqual(form.thumbnail.bbox.data, None)

    def test_with_unbound_image(self):
        doc = self.D()
        form = self.F(None, doc)
        self.assertEqual(form.image.filename.data, None)
        self.assertEqual(form.image.bbox.data, None)

        self.assertEqual(form.thumbnail.filename.data, None)
        self.assertEqual(form.thumbnail.bbox.data, None)

    def test_with_image(self):
        doc = self.D()
        with open(self.data('image.png')) as img:
            doc.image.save(img, 'image.jpg')
        doc.save()
        form = self.F(None, doc)
        self.assertEqual(form.image.filename.data, 'image.jpg')
        self.assertEqual(form.image.bbox.data, None)

    def test_with_image_and_bbox(self):
        doc = self.D()
        with open(self.data('image.png')) as img:
            doc.thumbnail.save(img, 'image.jpg', bbox=[10, 10, 100, 100])
        doc.save()
        form = self.F(None, doc)
        self.assertEqual(form.thumbnail.filename.data, 'image.jpg')
        self.assertEqual(form.thumbnail.bbox.data, [10, 10, 100, 100])

    def test_post_new(self):
        tmp_filename = 'xyz/image.png'
        with open(self.data('image.png')) as img:
            tmp_filename = tmp.save(img, tmp_filename)

        form = self.F(PostData({
            'image-filename': tmp_filename,
        }))

        self.assertEqual(form.image.filename.data, tmp_filename)
        self.assertEqual(form.image.bbox.data, None)

        doc = self.D()
        form.populate_obj(doc)

        self.assertIsNone(doc.image.bbox)
        self.assertTrue(doc.image.filename.endswith('.png'))
        self.assertIn(doc.image.filename, storage)
        self.assertNotIn(tmp_filename, tmp)

    def test_post_new_with_crop(self):
        tmp_filename = 'xyz/image.png'
        with open(self.data('image.png')) as img:
            tmp_filename = tmp.save(img, tmp_filename)

        form = self.F(PostData({
            'thumbnail-filename': tmp_filename,
            'thumbnail-bbox': '10,10,100,100',
        }))

        self.assertEqual(form.thumbnail.filename.data, tmp_filename)
        self.assertEqual(form.thumbnail.bbox.data, [10, 10, 100, 100])

        doc = self.D()
        form.populate_obj(doc)

        self.assertEqual(doc.thumbnail.bbox, [10, 10, 100, 100])
        self.assertTrue(doc.thumbnail.filename.endswith('.png'))
        self.assertIn(doc.thumbnail.filename, storage)
        self.assertNotIn(tmp_filename, tmp)
