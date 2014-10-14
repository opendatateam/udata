# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os.path import splitext, basename


def extension(filename):
    '''Properly extract the extension from filename'''
    filename = basename(filename)
    extension = None

    while '.' in filename:
        filename, ext = splitext(filename)
        if ext.startswith('.'):
            ext = ext[1:]
        extension = ext if not extension else ext + '.' + extension

    return extension
