# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from tempfile import NamedTemporaryFile

from udata.models import Badge, CERTIFIED, PUBLIC_SERVICE
from udata.tests import TestCase, DBTestMixin, CliTestMixin
from udata.core.organization.factories import OrganizationFactory


class BadgeCommandTest(CliTestMixin, DBTestMixin, TestCase):
    def toggle(self, path_or_id, kind):
        return self.cli('badges', 'toggle', path_or_id, kind)

    def test_toggle_badge_on(self):
        org = OrganizationFactory()

        self.toggle(str(org.id), PUBLIC_SERVICE)

        org.reload()
        self.assertEqual(org.badges[0].kind, PUBLIC_SERVICE)

    def test_toggle_badge_off(self):
        ps_badge = Badge(kind=PUBLIC_SERVICE)
        certified_badge = Badge(kind=CERTIFIED)
        org = OrganizationFactory(badges=[ps_badge, certified_badge])

        self.toggle(str(org.id), PUBLIC_SERVICE)

        org.reload()
        self.assertEqual(org.badges[0].kind, CERTIFIED)

    def test_toggle_badge_on_from_file(self):
        orgs = [OrganizationFactory() for _ in range(2)]

        with NamedTemporaryFile() as temp:
            temp.write('\n'.join((str(org.id) for org in orgs)))
            temp.flush()

            self.toggle(temp.name, PUBLIC_SERVICE)

        for org in orgs:
            org.reload()
            self.assertEqual(org.badges[0].kind, PUBLIC_SERVICE)
