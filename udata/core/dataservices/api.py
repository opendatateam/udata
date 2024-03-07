from flask import request
from mongoengine import Q

from udata.api import api, API
from udata.auth import admin_permission
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
        dataservice.save()
        return dataservice, 201

