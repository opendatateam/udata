from datetime import datetime
from flask import request
from flask_login import current_user
import mongoengine

from udata.api import api, API
from udata.auth import admin_permission
from udata.core.dataset.permissions import OwnablePermission
from udata.core.discussions.models import Discussion
from udata.core.spam.fields import potential_spam_fields
from udata.core.spam.models import POTENTIAL_SPAM
from udata.utils import id_or_404
from .models import Dataservice


ns = api.namespace('dataservices', 'Dataservices related operations')


@ns.route('/', endpoint='dataservices')
class DataservicesAPI(API):
    @api.secure
    @api.doc('create_dataservice', responses={400: 'Validation error'})
    @api.expect(Dataservice.__fields__)
    @api.marshal_with(Dataservice.__fields__, code=201)
    def post(self):
        dataservice = Dataservice(**request.json)
        dataservice.owner = current_user._get_current_object()

        try:
            dataservice.save()
        except mongoengine.errors.ValidationError as e:
            api.abort(400, e.message)

        return dataservice, 201
    

def patch(obj, request): 
    for key, value in request.json.items():
        field = obj.__fields__.get(key)
        if field is not None and not field.readonly:
            setattr(obj, key, value)

@ns.route('/<dataservice:dataservice>/', endpoint='dataservice')
class DataserviceAPI(API):
    @api.doc('get_dataservice')
    @api.marshal_with(Dataservice.__fields__)
    def get(self, dataservice):
        if dataservice.deleted_at and not OwnablePermission(dataservice).can():
            api.abort(410, 'Dataservice has been deleted')
        return dataservice
    
    @api.secure
    @api.doc('update_dataservice', responses={400: 'Validation error'})
    @api.expect(Dataservice.__fields__)
    @api.marshal_with(Dataservice.__fields__)
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

