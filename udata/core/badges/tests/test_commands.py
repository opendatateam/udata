from tempfile import NamedTemporaryFile

import pytest

from udata.core.organization.constants import CERTIFIED, PUBLIC_SERVICE
from udata.core.organization.factories import OrganizationFactory
from udata.models import Badge


@pytest.mark.usefixtures("clean_db")
class BadgeCommandTest:
    def toggle(self, path_or_id, kind):
        return self.cli("badges", "toggle", path_or_id, kind)

    def test_toggle_badge_on(self, cli):
        org = OrganizationFactory()

        cli("badges", "toggle", str(org.id), PUBLIC_SERVICE)

        org.reload()
        assert org.badges[0].kind == PUBLIC_SERVICE

    def test_toggle_badge_off(self, cli):
        ps_badge = Badge(kind=PUBLIC_SERVICE)
        certified_badge = Badge(kind=CERTIFIED)
        org = OrganizationFactory(badges=[ps_badge, certified_badge])

        cli("badges", "toggle", str(org.id), PUBLIC_SERVICE)

        org.reload()
        assert org.badges[0].kind == CERTIFIED

    def test_toggle_badge_on_from_file(self, cli):
        orgs = [OrganizationFactory() for _ in range(2)]

        with NamedTemporaryFile(mode="w") as temp:
            temp.write("\n".join((str(org.id) for org in orgs)))
            temp.flush()

            cli("badges", "toggle", temp.name, PUBLIC_SERVICE)

        for org in orgs:
            org.reload()
            assert org.badges[0].kind == PUBLIC_SERVICE
