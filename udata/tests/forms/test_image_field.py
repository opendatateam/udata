# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import shutil
import tempfile

from flask import url_for
from flask.ext import fs

from udata.models import db
from udata.forms import Form
from udata.forms.fields import ImageField
from udata.frontend.helpers import placeholder
from udata.tests import DBTestMixin, TestCase
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


class ImageFieldTest(DBTestMixin, TestCase):
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
        self.assertEqual(form.image(), ''.join((
            '<div class="image-picker-field" data-sizes="100" data-basename="image" data-endpoint="{0}">'.format(endpoint),
            '<div class="image-picker-preview">',
            '<img src="{0}" data-placeholder="{0}"/>'.format(placeholder(None, 'default')),
            '</div>',
            '<span class="image-picker-btn btn btn-default btn-file">',
            'Choose a picture',
            '<input id="image-filename" name="image-filename" type="hidden" value="">',
            '<input id="image-bbox" name="image-bbox" type="hidden" value="">',
            '</span>',
            '</div>',
        )))

        self.assertEqual(form.thumbnail.filename.data, None)
        self.assertEqual(form.thumbnail.bbox.data, None)
        self.assertEqual(form.thumbnail(), ''.join((
            '<div class="image-picker-field" data-sizes="16,32" data-basename="thumbnail" data-endpoint="{0}">'.format(endpoint),
            '<div class="image-picker-preview">',
            '<img src="{0}" data-placeholder="{0}"/>'.format(placeholder(None, 'default')),
            '</div>',
            '<span class="image-picker-btn btn btn-default btn-file">',
            'Choose a picture',
            '<input id="thumbnail-filename" name="thumbnail-filename" type="hidden" value="">',
            '<input id="thumbnail-bbox" name="thumbnail-bbox" type="hidden" value="">',
            '</span>',
            '</div>',
        )))

    def test_with_unbound_image(self):
        endpoint = url_for('storage.upload', name=tmp.name)
        doc = self.D()
        # doc.image.filename = 'image.jpg'
        # doc.thumbnail.filename = 'thumbnail.png'
        # doc.save()
        form = self.F(None, doc)
        self.assertEqual(form.image.filename.data, None)
        self.assertEqual(form.image.bbox.data, None)
        self.assertEqual(form.image(), ''.join((
            '<div class="image-picker-field" data-sizes="100" data-basename="image" data-endpoint="{0}">'.format(endpoint),
            '<div class="image-picker-preview">',
            '<img src="{0}" data-placeholder="{0}"/>'.format(placeholder(None, 'default')),
            '</div>',
            '<span class="image-picker-btn btn btn-default btn-file">',
            'Choose a picture',
            '<input id="image-filename" name="image-filename" type="hidden" value="">',
            '<input id="image-bbox" name="image-bbox" type="hidden" value="">',
            '</span>',
            '</div>'
        )))

        self.assertEqual(form.thumbnail.filename.data, None)
        self.assertEqual(form.thumbnail.bbox.data, None)
        self.assertEqual(form.thumbnail(), ''.join((
            '<div class="image-picker-field" data-sizes="16,32" data-basename="thumbnail" data-endpoint="{0}">'.format(endpoint),
            '<div class="image-picker-preview">',
            '<img src="{0}" data-placeholder="{0}"/>'.format(placeholder(None, 'default')),
            '</div>',
            '<span class="image-picker-btn btn btn-default btn-file">',
            'Choose a picture',
            '<input id="thumbnail-filename" name="thumbnail-filename" type="hidden" value="">',
            '<input id="thumbnail-bbox" name="thumbnail-bbox" type="hidden" value="">',
            '</span>',
            '</div>',
        )))

    def test_with_image(self):
        endpoint = url_for('storage.upload', name=tmp.name)
        doc = self.D()
        doc.image.filename = 'image.jpg'
        doc.thumbnail.filename = 'thumbnail.png'
        doc.save()
        form = self.F(None, doc)
        self.assertEqual(form.image.filename.data, 'image.jpg')
        self.assertEqual(form.image.bbox.data, None)
        self.assertEqual(form.image(), ''.join((
            '<div class="image-picker-field" data-sizes="100" data-basename="image" data-endpoint="{0}">'.format(endpoint),
            '<div class="image-picker-preview">',
            '<img src="{0}" data-placeholder="{1}"/>'.format(doc.image.url, placeholder(None, 'default')),
            '</div>',
            '<span class="image-picker-btn btn btn-default btn-file">',
            'Choose a picture',
            '<input id="image-filename" name="image-filename" type="hidden" value="">',
            '<input id="image-bbox" name="image-bbox" type="hidden" value="">',
            '</span>',
            '</div>',
        )))

        self.assertEqual(form.thumbnail.filename.data, 'thumbnail.png')
        self.assertEqual(form.thumbnail.bbox.data, None)
        self.assertEqual(form.thumbnail(), ''.join((
            '<div class="image-picker-field" data-sizes="16,32" data-basename="thumbnail" data-endpoint="{0}">'.format(endpoint),
            '<div class="image-picker-preview">',
            '<img src="{0}" data-placeholder="{1}"/>'.format(doc.thumbnail.url, placeholder(None, 'default')),
            '</div>',
            '<span class="image-picker-btn btn btn-default btn-file">',
            'Choose a picture',
            '<input id="thumbnail-filename" name="thumbnail-filename" type="hidden" value="">',
            '<input id="thumbnail-bbox" name="thumbnail-bbox" type="hidden" value="">',
            '</span>',
            '</div>',
        )))

    def test_with_image_and_bbox(self):
        endpoint = url_for('storage.upload', name=tmp.name)
        doc = self.D()
        doc.image.filename = 'image.jpg'
        doc.image.bbox = [10, 10, 100, 100]
        doc.save()
        form = self.F(None, doc)
        self.assertEqual(form.image.filename.data, 'image.jpg')
        self.assertEqual(form.image.bbox.data, [10, 10, 100, 100])
        self.assertEqual(form.image(), ''.join((
            '<div class="image-picker-field" data-sizes="100" data-basename="image" data-endpoint="{0}">'.format(endpoint),
            '<div class="image-picker-preview">',
            '<img src="{0}" data-placeholder="{1}"/>'.format(doc.image.url, placeholder(None, 'default')),
            '</div>',
            '<span class="image-picker-btn btn btn-default btn-file">',
            'Choose a picture',
            '<input id="image-filename" name="image-filename" type="hidden" value="">',
            '<input id="image-bbox" name="image-bbox" type="hidden" value="10,10,100,100">',
            '</span>',
            '</div>',
        )))

    def test_post_new(self):
        tmp_filename = 'xyz/image.png'
        with open(self.data('image.png')) as img:
            tmp.save(img, tmp_filename)

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
            tmp.save(img, tmp_filename)

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
