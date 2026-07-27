from datetime import UTC, datetime, timedelta

from udata.core.user.factories import UserFactory
from udata.geopf.models import GeopfToken
from udata.tests.api import PytestOnlyDBTestCase
from udata.tests.geopf import TEST_GEOPF_CONF


@TEST_GEOPF_CONF
class GeopfTokenTest(PytestOnlyDBTestCase):
    def test_round_trips_encrypted_fields(self):
        user = UserFactory()
        token = GeopfToken(
            user=user,
            access_token="plain-access",
            refresh_token="plain-refresh",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        token.save()

        raw = GeopfToken._get_collection().find_one({"_id": token.id})
        assert raw["access_token"] != "plain-access"
        assert raw["refresh_token"] != "plain-refresh"

        reloaded = GeopfToken.objects.get(id=token.id)
        assert reloaded.access_token == "plain-access"
        assert reloaded.refresh_token == "plain-refresh"

    def test_is_expired_true_in_the_past(self):
        user = UserFactory()
        token = GeopfToken(
            user=user,
            access_token="a",
            refresh_token="r",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        assert token.is_expired()

    def test_is_expired_false_in_the_future(self):
        user = UserFactory()
        token = GeopfToken(
            user=user,
            access_token="a",
            refresh_token="r",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert not token.is_expired()
