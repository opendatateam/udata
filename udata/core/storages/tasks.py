# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from PIL import Image

from udata.tasks import celery


@celery.task
def crop_image(filename, width, height):
    im = Image.open(filename)
    width, height = im.size   # Get dimensions

    left = (width - new_width) / 2
    top = (height - new_height) / 2
    right = (width + new_width) / 2
    bottom = (height + new_height) / 2

    im.crop((left, top, right, bottom))
