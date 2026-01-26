from datetime import UTC, date, datetime

from udata.api.fields import ISODateTime
from udata.core.dataset.factories import DatasetFactory

from . import APITestCase


class NextPageUrlTest(APITestCase):
    def test_dataset_search_with_endpoint_query_param(self):
        """Searching datasets with 'endpoint' as query param should not crash.

        Regression test for: TypeError: url_for() got multiple values for argument 'endpoint'
        https://errors.data.gouv.fr/organizations/sentry/issues/275602/
        """
        DatasetFactory.create_batch(25)

        response = self.get("/api/2/datasets/search/?endpoint=malicious&page=1")
        self.assert200(response)

        # next_page should be present and not contain the malicious endpoint param
        data = response.json
        assert data.get("next_page") is not None
        assert "endpoint=malicious" not in data["next_page"]


class FieldTest(APITestCase):
    def test_iso_date_time_field_format(self):
        # Use a fixed datetime to avoid microsecond differences
        fixed_naive = datetime(2022, 2, 22, 12, 30, 45)
        fixed_aware = datetime(2022, 2, 22, 12, 30, 45, tzinfo=UTC)
        datetime_date_aware_string = fixed_aware.isoformat()
        date_date = date.today()

        result = ISODateTime().format(str(fixed_naive))
        self.assertEqual(result, fixed_aware.isoformat())

        result = ISODateTime().format(fixed_naive)
        self.assertEqual(result, fixed_aware.isoformat())

        result = ISODateTime().format(fixed_aware)
        self.assertEqual(result, fixed_aware.isoformat())

        result = ISODateTime().format(datetime_date_aware_string)
        self.assertEqual(result, datetime_date_aware_string)

        result = ISODateTime().format(date_date)
        self.assertEqual(result, date_date.isoformat())
