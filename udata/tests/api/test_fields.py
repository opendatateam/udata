from datetime import date, datetime

import pytz

from udata.api.fields import ISODateTime
from udata.forms import Form, fields

from . import APITestCase

class FormWithBoolean(Form):
    without_default = fields.BooleanField()
    with_default = fields.BooleanField(default=False)


class FieldTest(APITestCase):
    def test_boolean(self):
        model_in_db = {
            'without_default': False,
            'with_default': True,
        }

        # With all fiels set in request it should be the value in the request
        print('With all fiels set in request')
        form = FormWithBoolean.from_json({
            'without_default': True,
            'with_default': False,
        }, obj=model_in_db, instance=model_in_db)
        self.assertEqual(form.without_default.data, True)
        self.assertEqual(form.with_default.data, False)

        # With None field in request it should be None or the default value if present
        print('With None field in request')
        form = FormWithBoolean.from_json({
            'without_default': None,
            'with_default': None,
        }, obj=model_in_db, instance=model_in_db)
        self.assertEqual(form.without_default.data, None)
        self.assertEqual(form.with_default.data, False)

        # Without any field in request it should be the values in the model
        print('Without any field in request')
        form = FormWithBoolean.from_json({}, obj=model_in_db, instance=model_in_db)
        self.assertEqual(form.without_default.data, model_in_db['without_default'])
        self.assertEqual(form.with_default.data, model_in_db['with_default'])

    def test_iso_date_time_field_format(self):
        datetime_date_naive = datetime.utcnow()
        datetime_date_aware = pytz.utc.localize(datetime_date_naive)
        datetime_date_aware_string = datetime_date_aware.isoformat()
        date_date = date.today()

        result = ISODateTime().format(str(datetime_date_naive))
        self.assertEqual(result, datetime_date_aware.isoformat())

        result = ISODateTime().format(datetime_date_naive)
        self.assertEqual(result, datetime_date_aware.isoformat())

        result = ISODateTime().format(datetime_date_aware)
        self.assertEqual(result, datetime_date_aware.isoformat())

        result = ISODateTime().format(datetime_date_aware_string)
        self.assertEqual(result, datetime_date_aware_string)

        result = ISODateTime().format(date_date)
        self.assertEqual(result, date_date.isoformat())
