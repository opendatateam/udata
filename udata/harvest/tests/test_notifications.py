from udata.core.user.factories import AdminFactory, UserFactory
from udata.harvest.notifications import validate_harvester_notifications
from udata.tests.api import PytestOnlyDBTestCase
from udata.tests.helpers import assert_equal_dates

from .factories import HarvestSourceFactory


class HarvestNotificationsTest(PytestOnlyDBTestCase):
    def test_pending_harvester_validations(self):
        source = HarvestSourceFactory()
        admin = AdminFactory()
        user = UserFactory()

        assert len(validate_harvester_notifications(user)) == 0

        notifications = validate_harvester_notifications(admin)

        assert len(notifications) == 1
        dt, details = notifications[0]
        assert_equal_dates(dt, source.created_at)
        assert details["id"] == source.id
        assert details["name"] == source.name
