from datetime import datetime
from flask import request
from flask_login import current_user
import mongoengine

from udata.api import api, API
from udata.api_fields import patch
from udata.core.dataset.permissions import OwnablePermission
from .models import Dataservice
from udata.models import db

ns = api.namespace('dataservices', 'Dataservices related operations')


@ns.route('/', endpoint='dataservices')
class DataservicesAPI(API):
    '''Datasets collection endpoint'''
    @api.doc('list_dataservices')
    @api.marshal_with(Dataservice.__page_fields__)
    def get(self):
        '''List or search all datasets'''
        return Dataservice.objects(archived=None, deleted=None, private=False).paginate(1, 10)

    @api.secure
    @api.doc('create_dataservice', responses={400: 'Validation error'})
    @api.expect(Dataservice.__write_fields__)
    @api.marshal_with(Dataservice.__read_fields__, code=201)
    def post(self):
        dataservice = patch(Dataservice(), request)
        dataservice.owner = current_user._get_current_object()

        try:
            dataservice.save()
        except mongoengine.errors.ValidationError as e:
            api.abort(400, e.message)

        return dataservice, 201

@ns.route('/<dataservice:dataservice>/', endpoint='dataservice')
class DataserviceAPI(API):
    @api.doc('get_dataservice')
    @api.marshal_with(Dataservice.__read_fields__)
    def get(self, dataservice):
        if dataservice.deleted_at and not OwnablePermission(dataservice).can():
            api.abort(410, 'Dataservice has been deleted')
        return dataservice
    
    @api.secure
    @api.doc('update_dataservice', responses={400: 'Validation error'})
    @api.expect(Dataservice.__write_fields__)
    @api.marshal_with(Dataservice.__read_fields__)
    def patch(self, dataservice):
        if dataservice.deleted_at:
            api.abort(410, 'dataservice has been deleted')

        OwnablePermission(dataservice).test()

        patch(dataservice, request)
        dataservice.modified_at = datetime.utcnow()

        try:
            dataservice.save()
            return dataservice
        except mongoengine.errors.ValidationError as e:
            api.abort(400, e.message)

    @api.secure
    @api.doc('delete_dataservice')
    @api.response(204, 'dataservice deleted')
    def delete(self, dataservice):
        if dataservice.deleted_at:
            api.abort(410, 'dataservice has been deleted')

        OwnablePermission(dataservice).test()

        dataservice.deleted_at = datetime.utcnow()
        dataservice.modified_at = datetime.utcnow()
        dataservice.save()

        return '', 204

