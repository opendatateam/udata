# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

from flask import Blueprint, request, jsonify
from flask_security import login_required
import flask_fs as fs

from . import utils


blueprint = Blueprint('storage', __name__)


@login_required
@blueprint.route('/upload/<name>/', methods=['POST'])
def upload(name):
    '''Handle upload on POST if authorized.'''
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'invalid request'}), 400

    storage = fs.by_name(name)

    file = request.files['file']
    filename = storage.save(file)

    file.seek(0)
    sha1 = utils.sha1(file)

    size = os.path.getsize(storage.path(filename)) if storage.root else None

    return jsonify({
        'success': True,
        'url': storage.url(filename, True),
        'filename': filename,
        'sha1': sha1,
        'size': size,
        'mime': utils.mime(filename),
    })
