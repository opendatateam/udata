# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from datetime import datetime

from udata.models import Reuse

from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import UserFactory
from udata.tests.helpers import assert_emit

from .. import TestCase, DBTestMixin


class ReuseModelTest(TestCase, DBTestMixin):
    def test_owned_by_user(self):
        user = UserFactory()
        reuse = ReuseFactory(owner=user)
        ReuseFactory(owner=UserFactory())

        result = Reuse.objects.owned_by(user)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], reuse)

    def test_owned_by_org(self):
        org = OrganizationFactory()
        reuse = ReuseFactory(organization=org)
        ReuseFactory(organization=OrganizationFactory())

        result = Reuse.objects.owned_by(org)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], reuse)

    def test_owned_by_org_or_user(self):
        user = UserFactory()
        org = OrganizationFactory()
        reuses = [ReuseFactory(owner=user), ReuseFactory(organization=org)]
        excluded = [ReuseFactory(owner=UserFactory()),
                    ReuseFactory(organization=OrganizationFactory())]

        result = Reuse.objects.owned_by(org, user)

        self.assertEqual(len(result), 2)
        for reuse in result:
            self.assertIn(reuse, reuses)

        for reuse in excluded:
            self.assertNotIn(reuse, result)

    def test_tags_normalized(self):
        user = UserFactory()
        tags = [' one another!', ' one another!', 'This IS a "tag"…']
        reuse = ReuseFactory(owner=user, tags=tags)
        self.assertEqual(len(reuse.tags), 2)
        self.assertEqual(reuse.tags[1], 'this-is-a-tag')

    def test_send_on_delete(self):
        reuse = ReuseFactory()
        with assert_emit(Reuse.on_delete):
            reuse.deleted = datetime.now()
            reuse.save()
