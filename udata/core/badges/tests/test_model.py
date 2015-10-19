# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.auth import login_user
from udata.models import db
from udata.tests import TestCase, DBTestMixin
from udata.tests.factories import UserFactory

from ..models import Badge, BadgeMixin


TEST = 'test'
OTHER = 'other'


class Fake(db.Document, BadgeMixin):
    __badges__ = {
        TEST: 'Test',
        OTHER: 'Other',
    }


class BadgeMixinTest(DBTestMixin, TestCase):
    def test_attributes(self):
        '''It should have a badge list'''
        fake = Fake.objects.create()
        self.assertIsInstance(fake.badges, (list, tuple))

    def test_get_badge_found(self):
        '''It allow to get a badge by kind if present'''
        fake = Fake.objects.create(badges=[
            Badge(kind=TEST),
            Badge(kind=OTHER)
        ])
        badge = fake.get_badge(TEST)
        self.assertEqual(badge.kind, TEST)

    def test_get_badge_not_found(self):
        '''It should return None if badge is absent'''
        fake = Fake.objects.create(badges=[Badge(kind=OTHER)])
        badge = fake.get_badge(TEST)
        self.assertIsNone(badge)

    def test_add_badge(self):
        '''It should a badge of a given kind'''
        fake = Fake.objects.create()

        result = fake.add_badge(TEST)

        self.assertEqual(len(fake.badges), 1)
        badge = fake.badges[0]
        self.assertEqual(result, badge)
        self.assertEqual(badge.kind, TEST)
        self.assertIsNotNone(badge.created)
        self.assertIsNone(badge.created_by)

    def test_add_2nd_badge(self):
        '''It should add badges to the top of the list'''
        fake = Fake.objects.create(badges=[Badge(kind=OTHER)])

        result = fake.add_badge(TEST)

        self.assertEqual(len(fake.badges), 2)
        badge = fake.badges[0]
        self.assertEqual(result, badge)
        self.assertEqual(badge.kind, TEST)

        self.assertEqual(fake.badges[-1].kind, OTHER)

    def test_add_badge_with_logged_user(self):
        '''It should track the user that add a badge'''
        user = UserFactory()
        fake = Fake.objects.create()

        login_user(user)
        result = fake.add_badge(TEST)

        self.assertEqual(len(fake.badges), 1)
        badge = fake.badges[0]
        self.assertEqual(result, badge)
        self.assertEqual(badge.kind, TEST)
        self.assertIsNotNone(badge.created)
        self.assertEqual(badge.created_by, user)

    def test_add_unknown_badge(self):
        '''It should not allow to add an unknown badge kind'''
        fake = Fake.objects.create()

        with self.assertRaises(db.ValidationError):
            fake.add_badge('unknown')

        self.assertEqual(len(fake.badges), 0)

    def test_remove_badge(self):
        '''It should remove a badge from its kind'''
        badge = Badge(kind=TEST)
        fake = Fake.objects.create(badges=[badge])

        fake.remove_badge(TEST)

        self.assertEqual(len(fake.badges), 0)

    def test_add_badge_twice(self):
        '''It should not duplicate badges'''
        fake = Fake.objects.create()

        result1 = fake.add_badge(TEST)
        result2 = fake.add_badge(TEST)

        self.assertEqual(len(fake.badges), 1)
        self.assertEqual(result1, result2)
        badge = fake.badges[0]
        self.assertEqual(badge.kind, TEST)
        self.assertIsNotNone(badge.created)
        self.assertIsNone(badge.created_by)
