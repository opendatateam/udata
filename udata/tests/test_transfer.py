# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import pytest

from udata.auth import login_user, PermissionDenied

from udata.features.transfer.factories import TransferFactory
from udata.features.transfer.actions import request_transfer, accept_transfer
from udata.features.transfer.notifications import (
    transfer_request_notifications
)
from udata.models import Member

from udata.utils import faker
from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory


pytestmark = pytest.mark.usefixtures('clean_db')


class TransferStartTest:
    def assert_transfer_started(self, subject, owner, recipient, comment):
        transfer = request_transfer(subject, recipient, comment)

        assert transfer.owner == owner
        assert transfer.recipient == recipient
        assert transfer.subject == subject
        assert transfer.comment == comment
        assert transfer.status == 'pending'

    def test_request_transfer_owner_to_user(self):
        user = UserFactory()
        dataset = VisibleDatasetFactory(owner=user)
        recipient = UserFactory()
        comment = faker.sentence()

        login_user(user)
        self.assert_transfer_started(dataset, user, recipient, comment)

    def test_request_transfer_organization_to_user(self):
        user = UserFactory()
        member = Member(user=user, role='admin')
        org = OrganizationFactory(members=[member])
        dataset = VisibleDatasetFactory(owner=user, organization=org)
        recipient = UserFactory()
        comment = faker.sentence()

        login_user(user)
        self.assert_transfer_started(dataset, org, recipient, comment)

    def test_request_transfer_user_to_organization(self):
        user = UserFactory()
        dataset = VisibleDatasetFactory(owner=user)
        recipient = OrganizationFactory()
        comment = faker.sentence()

        login_user(user)
        self.assert_transfer_started(dataset, user, recipient, comment)

    def test_request_transfer_not_authorized_not_owner(self):
        user = UserFactory()
        dataset = VisibleDatasetFactory(owner=UserFactory())
        recipient = UserFactory()
        comment = faker.sentence()

        login_user(user)
        with pytest.raises(PermissionDenied):
            request_transfer(dataset, recipient, comment)

    def test_request_transfer_not_authorized_not_admin(self):
        user = UserFactory()
        member = Member(user=user, role='editor')
        org = OrganizationFactory(members=[member])
        dataset = VisibleDatasetFactory(organization=org)
        recipient = UserFactory()
        comment = faker.sentence()

        login_user(user)
        with pytest.raises(PermissionDenied):
            request_transfer(dataset, recipient, comment)

    def test_request_transfer_to_self(self):
        user = UserFactory()
        dataset = VisibleDatasetFactory(owner=user)
        comment = faker.sentence()

        login_user(user)
        with pytest.raises(ValueError):
            self.assert_transfer_started(dataset, user, user, comment)

    def test_request_transfer_to_same_organization(self):
        user = UserFactory()
        member = Member(user=user, role='admin')
        org = OrganizationFactory(members=[member])
        dataset = VisibleDatasetFactory(owner=user, organization=org)
        comment = faker.sentence()

        login_user(user)

        with pytest.raises(ValueError):
            self.assert_transfer_started(dataset, org, org, comment)


@pytest.mark.options(USE_METRICS=True)
class TransferAcceptTest:
    def test_recipient_user_can_accept_transfer(self):
        owner = UserFactory()
        recipient = UserFactory()
        subject = VisibleDatasetFactory(owner=owner)
        transfer = TransferFactory(owner=owner,
                                   recipient=recipient,
                                   subject=subject)

        owner.reload()  # Needs updated metrics
        assert owner.metrics['datasets'] == 1

        recipient.reload()  # Needs updated metrics
        assert recipient.metrics['datasets'] == 0

        login_user(recipient)
        transfer = accept_transfer(transfer)

        assert transfer.status == 'accepted'

        subject.reload()
        assert subject.owner == recipient

        recipient.reload()
        assert recipient.metrics['datasets'] == 1

        owner.reload()
        assert owner.metrics['datasets'] == 0

    def test_org_admin_can_accept_transfer(self):
        owner = UserFactory()
        admin = UserFactory()
        org = OrganizationFactory(members=[Member(user=admin, role='admin')])
        subject = VisibleDatasetFactory(owner=owner)
        transfer = TransferFactory(owner=owner,
                                   recipient=org,
                                   subject=subject)

        owner.reload()  # Needs updated metrics
        assert owner.metrics['datasets'] == 1

        org.reload()  # Needs updated metrics
        assert org.metrics['datasets'] == 0

        admin.reload()  # Needs updated metrics
        assert admin.metrics['datasets'] == 0

        login_user(admin)
        transfer = accept_transfer(transfer)

        assert transfer.status == 'accepted'

        subject.reload()
        assert subject.organization == org
        assert subject.owner is None

        org.reload()
        assert org.metrics['datasets'] == 1

        admin.reload()
        assert admin.metrics['datasets'] == 0

        owner.reload()
        assert owner.metrics['datasets'] == 0

    def test_org_editor_cant_accept_transfer(self):
        owner = UserFactory()
        editor = UserFactory()
        org = OrganizationFactory(members=[Member(user=editor, role='editor')])
        subject = VisibleDatasetFactory(organization=org)
        transfer = TransferFactory(owner=owner,
                                   recipient=org,
                                   subject=subject)

        login_user(editor)
        with pytest.raises(PermissionDenied):
            accept_transfer(transfer)


class TransferNotificationsTest:
    def test_pending_transfer_request_for_user(self):
        user = UserFactory()
        datasets = VisibleDatasetFactory.create_batch(2, owner=user)
        recipient = UserFactory()
        comment = faker.sentence()
        transfers = {}

        login_user(user)
        for dataset in datasets:
            transfer = request_transfer(dataset, recipient, comment)
            transfers[transfer.id] = transfer

        assert len(transfer_request_notifications(user)) == 0

        notifications = transfer_request_notifications(recipient)
        assert len(notifications) == len(datasets)
        for dt, details in notifications:
            transfer = transfers[details['id']]
            assert details['subject']['class'] == 'dataset'
            assert details['subject']['id'] == transfer.subject.id

    def test_pending_transfer_request_for_org(self):
        user = UserFactory()
        datasets = VisibleDatasetFactory.create_batch(2, owner=user)
        recipient = UserFactory()
        member = Member(user=recipient, role='editor')
        org = OrganizationFactory(members=[member])
        comment = faker.sentence()
        transfers = {}

        login_user(user)
        for dataset in datasets:
            transfer = request_transfer(dataset, org, comment)
            transfers[transfer.id] = transfer

        assert len(transfer_request_notifications(user)) == 0

        notifications = transfer_request_notifications(recipient)
        assert len(notifications) == len(datasets)
        for dt, details in notifications:
            transfer = transfers[details['id']]
            assert details['subject']['class'] == 'dataset'
            assert details['subject']['id'] == transfer.subject.id
