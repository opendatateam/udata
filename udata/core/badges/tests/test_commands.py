# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from tempfile import NamedTemporaryFile

from udata.models import Badge, CERTIFIED, PUBLIC_SERVICE
from udata.tests import TestCase, DBTestMixin
from udata.core.organization.factories import OrganizationFactory
from udata.core.badges.commands import toggle


class BadgeCommandTest(DBTestMixin, TestCase):

    def test_toggle_badge_on(self):
        org = OrganizationFactory()
        toggle(str(org.id), PUBLIC_SERVICE)
        org.reload()
        self.assertEqual(org.badges[0].kind, PUBLIC_SERVICE)

    def test_toggle_badge_off(self):
        ps_badge = Badge(kind=PUBLIC_SERVICE)
        certified_badge = Badge(kind=CERTIFIED)
        org = OrganizationFactory(badges=[ps_badge, certified_badge])
        toggle(str(org.id), PUBLIC_SERVICE)
        org.reload()
        self.assertEqual(org.badges[0].kind, CERTIFIED)

    def test_toggle_badge_on_from_file(self):
        orgs = [OrganizationFactory() for _ in range(2)]

        with NamedTemporaryFile() as temp:
            temp.write('\n'.join((str(org.id) for org in orgs)))
            temp.flush()

            toggle(temp.name, PUBLIC_SERVICE)

        for org in orgs:
            org.reload()
            self.assertEqual(org.badges[0].kind, PUBLIC_SERVICE)
