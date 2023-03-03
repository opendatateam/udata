import logging

import pytest

import flask_storage as fs

from udata.models import db
from udata.forms import Form
from udata.forms.fields import ImageField
from udata.tests.helpers import data_path
from udata.core.storages import tmp

log = logging.getLogger(__name__)

SIZES = [16, 32]

storage = fs.Storage('test')


class PostData(dict):
    def getlist(self, key):
        value = self[key]
        if not isinstance(value, (list, tuple)):
            value = [value]
        return value


@pytest.mark.usefixtures('clean_db')
class ImageFieldTest:
    class D(db.Document):
        image = db.ImageField(fs=storage)
        thumbnail = db.ImageField(fs=storage, thumbnails=SIZES)

    class F(Form):
        image = ImageField()
        thumbnail = ImageField(sizes=SIZES)

    @pytest.fixture(autouse=True)
    def fs_root(self, instance_path, app):
        app.config['FS_ROOT'] = str(instance_path / 'fs')
        fs.init_app(app, storage, tmp)

    def test_empty(self):
        form = self.F()
        assert form.image.filename.data is None
        assert form.image.bbox.data is None

        assert form.thumbnail.filename.data is None
        assert form.thumbnail.bbox.data is None

    def test_with_unbound_image(self):
        doc = self.D()
        form = self.F(None, obj=doc)
        assert form.image.filename.data is None
        assert form.image.bbox.data is None

        assert form.thumbnail.filename.data is None
        assert form.thumbnail.bbox.data is None

    def test_with_image(self):
        doc = self.D()
        with open(data_path('image.png'), 'rb') as img:
            doc.image.save(img, 'image.jpg')
        doc.save()
        form = self.F(None, obj=doc)
        assert form.image.filename.data == 'image.jpg'
        assert form.image.bbox.data is None

    def test_with_image_and_bbox(self):
        doc = self.D()
        with open(data_path('image.png'), 'rb') as img:
            doc.thumbnail.save(img, 'image.jpg', bbox=[10, 10, 100, 100])
        doc.save()
        form = self.F(None, obj=doc)
        assert form.thumbnail.filename.data == 'image.jpg'
        assert form.thumbnail.bbox.data == [10, 10, 100, 100]

    def test_post_new(self):
        tmp_filename = 'xyz/image.png'
        with open(data_path('image.png'), 'rb') as img:
            tmp_filename = tmp.save(img, tmp_filename)

        form = self.F(PostData({
            'image-filename': tmp_filename,
        }))

        assert form.image.filename.data == tmp_filename
        assert form.image.bbox.data is None

        doc = self.D()
        form.populate_obj(doc)

        assert doc.image.bbox is None
        assert doc.image.filename.endswith('.png')
        assert doc.image.filename in storage
        assert tmp_filename not in tmp

    def test_post_new_with_crop(self):
        tmp_filename = 'xyz/image.png'
        with open(data_path('image.png'), 'rb') as img:
            tmp_filename = tmp.save(img, tmp_filename)

        form = self.F(PostData({
            'thumbnail-filename': tmp_filename,
            'thumbnail-bbox': '10,10,100,100',
        }))

        assert form.thumbnail.filename.data == tmp_filename
        assert form.thumbnail.bbox.data == [10, 10, 100, 100]

        doc = self.D()
        form.populate_obj(doc)

        assert doc.thumbnail.bbox == [10, 10, 100, 100]
        assert doc.thumbnail.filename.endswith('.png')
        assert doc.thumbnail.filename in storage
        assert tmp_filename not in tmp
