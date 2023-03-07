from datetime import date, datetime

import pytz

from udata.api.fields import ISODateTime

from . import APITestCase


class FieldTest(APITestCase):
    def test_iso_date_time_field_format(self):
        datetime_date_naive = datetime.now()
        datetime_date_aware = pytz.utc.localize(datetime_date_naive)
        date_date = date.today()

        result = ISODateTime().format(str(datetime_date_naive))
        self.assertEqual(result, datetime_date_aware.isoformat())

        result = ISODateTime().format(datetime_date_naive)
        self.assertEqual(result, datetime_date_aware.isoformat())

        result = ISODateTime().format(datetime_date_aware)
        self.assertEqual(result, datetime_date_aware.isoformat())

        result = ISODateTime().format(date_date)
        self.assertEqual(result, date_date.isoformat())
