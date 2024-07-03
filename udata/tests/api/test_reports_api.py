from typing import List
from flask import url_for

from udata.core.dataset.factories import (DatasetFactory)
from udata.core.dataset.models import Dataset
from udata.core.reports.models import Report
from udata.core.reports.constants import REASON_ILLEGAL_CONTENT, REASON_SPAM, reports_reasons_translations
from udata.i18n import gettext as _

from . import APITestCase


class ReportsReasonsAPITest(APITestCase):
    modules = []

    def test_reports_reasons_api(self):
        response = self.get(url_for('api.reports_reasons'))
        self.assert200(response)
        self.assertEqual(response.json, reports_reasons_translations())

class ReportsAPITest(APITestCase):
    modules = []

    def test_reports_api_create(self):
        user = self.login()
        illegal_dataset = DatasetFactory.create(owner=user)
        spam_dataset = DatasetFactory.create(owner=user)

        response = self.post(url_for('api.reports'), {
            'object_type': 'Dataset',
            'object_id': illegal_dataset.id,
            'message': 'This is not appropriate',
            'reason': REASON_ILLEGAL_CONTENT,
        })
        self.assert201(response)
        self.assertEqual(Report.objects.count(), 1)

        response = self.post(url_for('api.reports'), {
            'object_type': 'Dataset',
            'object_id': spam_dataset.id,
            'message': 'This is spammy',
            'reason': REASON_SPAM,
        })
        self.assert201(response)
        self.assertEqual(Report.objects.count(), 2)

        reports: List[Report] = list(Report.objects())
        self.assertEqual(Dataset.__name__, reports[0].object_type)
        self.assertEqual(illegal_dataset.id, reports[0].object_id)
        self.assertEqual('This is not appropriate', reports[0].message)
        self.assertEqual(REASON_ILLEGAL_CONTENT, reports[0].reason)
        self.assertEqual(user.id, reports[0].by.id)
        
        self.assertEqual(Dataset.__name__, reports[1].object_type)
        self.assertEqual(spam_dataset.id, reports[1].object_id)
        self.assertEqual('This is spammy', reports[1].message)
        self.assertEqual(REASON_SPAM, reports[1].reason)
        self.assertEqual(user.id, reports[1].by.id)

        response = self.delete(url_for('api.dataset', dataset=illegal_dataset))
        self.assert204(response)
        
        reports[0].reload()
        self.assertEqual(Dataset.__name__, reports[0].object_type)
        self.assertEqual(illegal_dataset.id, reports[0].object_id)
        self.assertEqual('This is not appropriate', reports[0].message)
        self.assertEqual(REASON_ILLEGAL_CONTENT, reports[0].reason)
        self.assertEqual(user.id, reports[0].by.id)
        self.assertIsNotNone(reports[0].object_deleted_at)

        reports[1].reload()
        self.assertEqual(Dataset.__name__, reports[1].object_type)
        self.assertEqual(spam_dataset.id, reports[1].object_id)
        self.assertEqual('This is spammy', reports[1].message)
        self.assertEqual(REASON_SPAM, reports[1].reason)
        self.assertEqual(user.id, reports[1].by.id)
        self.assertIsNone(reports[1].object_deleted_at)

        # We should take action on manual delete in the database too
        spam_dataset.delete()

        reports[1].reload()
        self.assertIsNotNone(reports[1].object_deleted_at)

        response = self.get(url_for('api.reports'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 2)

