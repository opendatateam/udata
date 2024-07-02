from flask import request
from flask_login import current_user
import mongoengine

from udata.api import api, API, fields
from udata.api_fields import patch
from .models import Report
from .constants import reports_reasons_translations

ns = api.namespace('reports', 'User reported objects related operations (beta)')

@ns.route('/', endpoint='reports')
class ReportsAPI(API):
    @api.doc('list_reports')
    @api.expect(Report.__index_parser__)
    @api.marshal_with(Report.__page_fields__)
    def get(self):
        query = Report.objects

        return Report.apply_sort_filters_and_pagination(query)

    @api.secure
    @api.doc('create_report', responses={400: 'Validation error'})
    @api.expect(Report.__write_fields__)
    @api.marshal_with(Report.__read_fields__, code=201)
    def post(self):
        report = patch(Report(), request)
        report.by = current_user._get_current_object()

        try:
            report.save()
        except mongoengine.errors.ValidationError as e:
            api.abort(400, e.message)

        return report, 201
    

@ns.route('/reasons/', endpoint='reports_reasons')
class ReportsReasonsAPI(API):
    @api.doc('list_reports_reasons')
    @ns.response(200, "dictionnary of available reasons associated with their labels", fields.Raw)
    def get(self):
        return reports_reasons_translations()
