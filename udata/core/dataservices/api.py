from datetime import datetime
from flask import request
from flask_login import current_user
import mongoengine

from udata.api import api, API
from udata.api_fields import patch
from udata.core.dataset.permissions import OwnablePermission
from udata.core.followers.api import FollowAPI
from .models import Dataservice

ns = api.namespace('dataservices', 'Dataservices related operations (beta)')


@ns.route('/', endpoint='dataservices')
class DataservicesAPI(API):
    '''Dataservices collection endpoint'''
    @api.doc('list_dataservices')
    @api.expect(Dataservice.__index_parser__)
    @api.marshal_with(Dataservice.__page_fields__)
    def get(self):
        '''List or search all dataservices'''
        query = Dataservice.objects.visible()

        return Dataservice.apply_sort_filters_and_pagination(query)

    @api.secure
    @api.doc('create_dataservice', responses={400: 'Validation error'})
    @api.expect(Dataservice.__write_fields__)
    @api.marshal_with(Dataservice.__read_fields__, code=201)
    def post(self):
        dataservice = patch(Dataservice(), request)
        if not dataservice.owner and not dataservice.organization:
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


@ns.route('/<id>/followers/', endpoint='dataservice_followers')
@ns.doc(get={'id': 'list_dataservice_followers'},
        post={'id': 'follow_dataservice'},
        delete={'id': 'unfollow_dataservice'})
class DataserviceFollowersAPI(FollowAPI):
    model = Dataservice
