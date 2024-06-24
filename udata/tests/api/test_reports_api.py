from flask import url_for

from udata.core.dataset.factories import (DatasetFactory)
from udata.core.dataset.models import Dataset
from udata.core.reports.models import Report
from udata.core.reports.constants import REASON_ILLEGAL_CONTENT
from udata.i18n import gettext as _

from . import APITestCase

class ReportsAPITest(APITestCase):
    modules = []

    def test_reports_api_create(self):
        user = self.login()
        dataset = DatasetFactory.create()

        response = self.post(url_for('api.reports'), {
            'object_type': 'Dataset',
            'object_id': dataset.id,
            'message': 'This is not appropriate',
            'reason': REASON_ILLEGAL_CONTENT,
        })
        self.assert201(response)
        self.assertEqual(Report.objects.count(), 1)

        report = Report.objects.first()
        self.assertEqual(Dataset.__name__, report.object_type)
        self.assertEqual(dataset.id, report.object_id)
        self.assertEqual('This is not appropriate', report.message)
        self.assertEqual(REASON_ILLEGAL_CONTENT, report.reason)
        self.assertEqual(user.id, report.by.id)
