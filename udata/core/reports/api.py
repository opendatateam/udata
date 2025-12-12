from flask import request
from flask_login import current_user

from udata.api import API, api, fields
from udata.api_fields import patch
from udata.auth import admin_permission

from .constants import REASON_AUTO_SPAM, reports_reasons_translations
from .models import Report

ns = api.namespace("reports", "User reported objects related operations (beta)")


@ns.route("/", endpoint="reports")
class ReportsAPI(API):
    @api.doc("list_reports")
    @api.expect(Report.__index_parser__)
    @api.marshal_with(Report.__page_fields__)
    @api.secure(admin_permission)
    def get(self):
        query = Report.objects

        return Report.apply_pagination(Report.apply_sort_filters(query))

    @api.doc("create_report", responses={400: "Validation error"})
    @api.expect(Report.__write_fields__)
    @api.marshal_with(Report.__read_fields__, code=201)
    def post(self):
        report = patch(Report(), request)
        if current_user.is_authenticated:
            report.by = current_user._get_current_object()

        report.save()
        return report, 201


@ns.route("/<report:report>/", endpoint="report")
class ReportAPI(API):
    @api.doc("get_report")
    @api.marshal_with(Report.__read_fields__)
    @api.secure(admin_permission)
    def get(self, report):
        return report

    @api.doc("update_report", responses={400: "Validation error"})
    @api.secure(admin_permission)
    @api.expect(Report.__write_fields__)
    @api.marshal_with(Report.__read_fields__, code=200)
    def patch(self, report):
        dismiss_has_changed = (
            "dismissed_at" in request.json and request.json["dismissed_at"] != report.dismissed_at
        )

        report = patch(report, request)
        if dismiss_has_changed:
            report.dismissed_by = (
                current_user._get_current_object() if report.dismissed_at else None
            )

            # For auto_spam reports, execute callbacks when dismissing (marking as not spam)
            # We must save BEFORE executing callbacks so that is_spam() returns False
            # when the @spam_protected decorator re-checks during callback execution
            if report.dismissed_at and report.reason == REASON_AUTO_SPAM and report.callbacks:
                callbacks = report.callbacks
                report.callbacks = {}
                report.save()
                # Execute callbacks after save
                subject = (
                    report.subject.fetch() if hasattr(report.subject, "fetch") else report.subject
                )
                for method_name, call_info in callbacks.items():
                    method = getattr(subject, method_name, None)
                    if method:
                        method(*call_info.get("args", []), **call_info.get("kwargs", {}))
                return report, 200

        report.save()
        return report, 200


@ns.route("/reasons/", endpoint="reports_reasons")
class ReportsReasonsAPI(API):
    @api.doc("list_reports_reasons")
    @ns.response(200, "list of available reasons associated with their labels", fields.Raw)
    def get(self):
        return reports_reasons_translations()
