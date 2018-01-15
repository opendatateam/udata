# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from tempfile import NamedTemporaryFile

from mock import patch

from udata.models import Badge, CERTIFIED, PUBLIC_SERVICE
from udata.tests import TestCase, DBTestMixin
from udata.core.organization.factories import OrganizationFactory

from click.testing import CliRunner
from udata.commands import cli


class BadgeCommandTest(DBTestMixin, TestCase):
    def toggle(self, path_or_id, kind):
        runner = CliRunner()
        with patch.object(cli, 'create_app', return_value=self.app):
            result = runner.invoke(cli, ['badges', 'toggle', path_or_id, kind],
                                   catch_exceptions=False)
        self.assertEqual(result.exit_code, 0,
                         'The command failed with exit code {0.exit_code} '
                         'and the following output:\n{0.output}'
                         .format(result))
        return result

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
