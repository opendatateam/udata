# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.api import api, API, fields

ns = api.namespace('admin', 'Admin related operations')


common_doc = {
    'params': {'dataset': 'The dataset ID or slug'}
}

menu_item = api.model('MenuItem', {
    'url': fields.String,
    'label': fields.String,
})


@ns.route('/menu/', endpoint='menu')
class AdminMenuAPI(API):

    @api.doc(id='get_admin_menu')
    @api.marshal_list_with(menu_item)
    def get(self):
        '''Get the Admin menu layout'''
        pass


@ns.route('/layout/', endpoint='layout')
class AdminLayoutAPI(API):

    @api.doc(id='get_admin_layout')
    @api.marshal_list_with(menu_item)
    def get(self):
        '''Get the Admin menu layout'''
        pass
