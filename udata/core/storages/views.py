# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import Blueprint, request, jsonify, make_response
from flask.views import MethodView

from flask.ext.security import login_required

from . import resources_storage, avatars_storage, images_storage


blueprint = Blueprint('storage', __name__, url_prefix='/s')


class StorageView(MethodView):
    '''
    View which will handle all upload requests sent by Fine Uploader.

    Handles POST and DELETE requests.
    '''
    storage = None
    # decorators = [login_required]

    def post(self):
        '''Handle upload on post.'''
        if not 'file' in request.files:
            return make_response(jsonify({'success': False, 'error': 'invalid request'}), 400)

        filename = self.storage.save(request.files['file'])
        return jsonify({
            'success': True,
            'url': self.storage.url(filename),
        })

    def delete(self, uuid):
        '''Handle delete by UUID.'''
        try:
            handle_delete(uuid)
            return make_response(200, { "success": True })
        except Exception, e:
            return make_response(400, { "success": False, "error": e.message })

    @classmethod
    def register(cls, blueprint):
        blueprint.add_url_rule('/{0}'.format(cls.storage.name), methods=['POST'],
            view_func=login_required(cls.as_view(b'add_{0}'.format(cls.storage.name[:-1]))))
        blueprint.add_url_rule('/{0}/<uuid>'.format(cls.storage.name),
            view_func=cls.as_view(b'del_{0}'.format(cls.storage.name[:-1])), methods=['DELETE'])


class ResourcesStorage(StorageView):
    storage = resources_storage

ResourcesStorage.register(blueprint)



class ImagesStorage(StorageView):
    storage = images_storage

ImagesStorage.register(blueprint)

# @blueprint.route('/resource', methods=['POST'])
# @login_required
# def add_resource():
#     filename = resources_storage.save(request.files['file'])
#     return jsonify({'url': resources_storage.url(filename)})


# @blueprint.route('/post_thumbnails', methods=['POST'])
# @login_required
# def add_post_thumbnail():
#     filename = resources_storage.save(request.files['file'])
#     return jsonify({'url': resources_storage.url(filename)})


# @blueprint.route('/avatar', methods=['POST'])
# @login_required
# def add_avatar():
#     filename = avatars_storage.save(request.files['file'])
#     return jsonify({'url': avatars_storage.url(filename)})


# @blueprint.route('/image', methods=['POST'])
# @login_required
# def add_image():
#     filename = images_storage.save(request.files['file'])
#     return jsonify({'url': images_storage.url(filename)})
