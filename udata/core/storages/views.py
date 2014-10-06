# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import Blueprint, request, jsonify

from flask.ext.security import login_required

from flask.ext import fs

from . import utils


blueprint = Blueprint('storage', __name__, url_prefix='/s')


@login_required
@blueprint.route('/<name>/', methods=['POST'])
def upload(name):
    '''Handle upload on POST if authorized.'''
    if not 'file' in request.files:
        return jsonify({'success': False, 'error': 'invalid request'}), 400

    storage = fs.by_name(name)

    file = request.files['file']
    filename = storage.save(file)

    file.seek(0)
    sha1 = utils.sha1(file)

    return jsonify({
        'success': True,
        'url': storage.url(filename),
        'filename': filename,
        'sha1': sha1
    })
