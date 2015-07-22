# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os

from PIL import Image

from udata.app import standalone, create_app

log = logging.getLogger(__name__)

app = standalone(create_app())


DEFAULT_SIZES = [128]  # , 25]
MAX = 10


def make_thumbnail(filename, size, crop=None):
    base, ext = os.path.splitext(filename)
    image = Image.open(filename)
    if crop:
        pass
    else:
        thumbnail = center_thumbnail(image, size)
    thumbnail.save(base + '-' + str(size) + ext)


def center_thumbnail(image, size):
    result = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    if image.size[0] > image.size[1]:
        new_size = (size, image.size[1] * size / image.size[0])
    else:
        new_size = (image.size[0] * size / image.size[1], size)

    resized = image.resize(new_size, Image.ANTIALIAS)
    position = ((size - new_size[0]) / 2, (size - new_size[1]) / 2)
    result.paste(resized, position)
    return result
