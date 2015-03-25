# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.auth import login_user, PermissionDenied
from udata.features.transfer.actions import request_transfer
from udata.models import Member

from . import TestCase, DBTestMixin
from .factories import faker, DatasetFactory, UserFactory, OrganizationFactory


class TransferTest(TestCase, DBTestMixin):
    def assert_transfer_started(self, subject, owner, recipient, comment):
        transfer = request_transfer(subject, recipient, comment)

        self.assertEqual(transfer.owner, owner)
        self.assertEqual(transfer.recipient, recipient)
        self.assertEqual(transfer.subject, subject)
        self.assertEqual(transfer.comment, comment)
        self.assertEqual(transfer.status, 'pending')

    def test_request_transfer_owner_to_user(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        recipient = UserFactory()
        comment = faker.sentence()

        login_user(user)
        self.assert_transfer_started(dataset, user, recipient, comment)

    def test_request_transfer_organization_to_user(self):
        user = UserFactory()
        member = Member(user=user, role='admin')
        org = OrganizationFactory(members=[member])
        dataset = DatasetFactory(owner=user, organization=org)
        recipient = UserFactory()
        comment = faker.sentence()

        login_user(user)
        self.assert_transfer_started(dataset, org, recipient, comment)

    def test_request_transfer_user_to_organization(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        recipient = OrganizationFactory()
        comment = faker.sentence()

        login_user(user)
        self.assert_transfer_started(dataset, user, recipient, comment)

    def test_request_transfer_not_authorized_not_owner(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=UserFactory())
        recipient = UserFactory()
        comment = faker.sentence()

        login_user(user)
        with self.assertRaises(PermissionDenied):
            request_transfer(dataset, recipient, comment)

    def test_request_transfer_not_authorized_not_admin(self):
        user = UserFactory()
        member = Member(user=user, role='editor')
        org = OrganizationFactory(members=[member])
        dataset = DatasetFactory(owner=user, organization=org)
        recipient = UserFactory()
        comment = faker.sentence()

        login_user(user)
        with self.assertRaises(PermissionDenied):
            request_transfer(dataset, recipient, comment)

    def test_request_transfer_to_self(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        comment = faker.sentence()

        login_user(user)
        with self.assertRaises(ValueError):
            self.assert_transfer_started(dataset, user, user, comment)

    def test_request_transfer_to_same_organization(self):
        user = UserFactory()
        member = Member(user=user, role='admin')
        org = OrganizationFactory(members=[member])
        dataset = DatasetFactory(owner=user, organization=org)
        comment = faker.sentence()

        login_user(user)

        with self.assertRaises(ValueError):
            self.assert_transfer_started(dataset, org, org, comment)
