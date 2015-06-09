# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import url_for

from udata.models import (
    Dataset, DatasetBadge, Organization, OrganizationBadge, Member
)
from udata.core.user.views import blueprint as user_bp
from udata.core.badges.models import PUBLIC_SERVICE, PIVOTAL_DATA
from udata.core.badges.signals import on_badge_added

from .api import APITestCase
from .factories import UserFactory


class BadgesTest(APITestCase):
    def create_app(self):
        app = super(BadgesTest, self).create_app()
        app.register_blueprint(user_bp)
        return app

    def test_new_organization_badge(self):
        user = self.login()
        organization = Organization.objects.create(
            name='Test organization',
            description='Description'
        )

        response = self.post(url_for('api.badges'), {
            'subject': organization.id,
            'kind': PUBLIC_SERVICE,
        })
        self.assertStatus(response, 201)

        organization.reload()
        self.assertEqual(organization.metrics['badges'], 1)

        badges = OrganizationBadge.objects(subject=organization)
        self.assertEqual(len(badges), 1)

        badge = badges[0]
        self.assertEqual(badge.created_by, user)
        self.assertIsNotNone(badge.created)
        self.assertIsNone(badge.removed)
        self.assertIsNone(badge.removed_by)
        self.assertEqual(badge.kind, 'public-service')

    def test_new_dataset_badge(self):
        user = self.login()
        organization = Organization.objects.create(
            name='Test organization',
            description='Description'
        )
        dataset = Dataset.objects.create(
            title='Test dataset',
            organization=organization
        )
        response = self.post(url_for('api.badges'), {
            'subject': dataset.id,
            'kind': PIVOTAL_DATA,
        })
        self.assertStatus(response, 201)

        dataset.reload()
        self.assertEqual(dataset.metrics['badges'], 1)

        badges = DatasetBadge.objects(subject=dataset)
        self.assertEqual(len(badges), 1)

        badge = badges[0]
        self.assertEqual(badge.created_by, user)
        self.assertIsNotNone(badge.created)
        self.assertIsNone(badge.removed)
        self.assertIsNone(badge.removed_by)
        self.assertEqual(badge.kind, 'pivotal-data')

    def test_new_badge_missing_subject(self):
        self.login()
        response = self.post(url_for('api.badges'), {
            'kind': PUBLIC_SERVICE,
        })
        self.assertStatus(response, 400)

    def test_new_badge_missing_kind(self):
        self.login()
        organization = Organization.objects.create(
            name='Test organization',
            description='Description'
        )
        response = self.post(url_for('api.badges'), {
            'subject': organization.id,
        })
        self.assertStatus(response, 400)

    def test_list_badges(self):
        user = UserFactory()
        organization = Organization.objects.create(
            name='Test organization',
            description='Description'
        )
        OrganizationBadge.objects.create(
            subject=organization.id,
            kind=PUBLIC_SERVICE,
            created=datetime.now(),
            created_by=user
        )
        # Creating a removed badge that shouldn't show up in response.
        OrganizationBadge.objects.create(
            subject=organization.id,
            kind=PUBLIC_SERVICE,
            created=datetime.now(),
            created_by=user,
            removed=datetime.now(),
            removed_by=user
        )
        response = self.get(url_for('api.badges'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)

    def test_list_badges_with_removed(self):
        user = UserFactory()
        organization = Organization.objects.create(
            name='Test organization',
            description='Description'
        )
        OrganizationBadge.objects.create(
            subject=organization.id,
            kind=PUBLIC_SERVICE,
            created=datetime.now(),
            created_by=user
        )
        # Creating a removed badge that should show up in response.
        OrganizationBadge.objects.create(
            subject=organization.id,
            kind=PUBLIC_SERVICE,
            created=datetime.now(),
            created_by=user,
            removed=datetime.now(),
            removed_by=user
        )

        response = self.get(url_for('api.badges', removed=True))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 2)

    def test_get_badge(self):
        user = UserFactory()
        organization = Organization.objects.create(
            name='Test organization',
            description='Description'
        )
        badge = OrganizationBadge.objects.create(
            subject=organization.id,
            kind=PUBLIC_SERVICE,
            created=datetime.now(),
            created_by=user
        )
        response = self.get(url_for('api.badge',
                            **{'for': organization.id, 'id': badge.id}))
        self.assert200(response)

        data = response.json
        self.assertEqual(data['subject'], str(organization.id))
        self.assertIsNotNone(data['created'])
        self.assertEqual(data['created_by']['id'], str(user.id))
        self.assertIsNone(data['removed'])
        self.assertIsNone(data['removed_by'])
        self.assertEqual(data['kind'], 'public-service')

    def test_remove_organization_badge(self):
        user = self.login()
        member = Member(user=user, role='admin')
        organization = Organization.objects.create(
            name='Test organization',
            description='Description',
            members=[member]
        )
        badge = OrganizationBadge.objects.create(
            subject=organization.id,
            kind=PUBLIC_SERVICE,
            created=datetime.now(),
            created_by=user
        )
        on_badge_added.send(badge)  # Updating metrics.
        organization.reload()
        self.assertEqual(organization.metrics['badges'], 1)

        response = self.delete(url_for('api.badge', id=badge.id))
        self.assertStatus(response, 204)

        organization.reload()
        self.assertEqual(organization.metrics['badges'], 0)

    def test_remove_dataset_badge(self):
        user = self.login()
        member = Member(user=user, role='admin')
        organization = Organization.objects.create(
            name='Test organization',
            description='Description',
            members=[member]
        )
        dataset = Dataset.objects.create(
            title='Test dataset',
            organization=organization
        )
        badge = DatasetBadge.objects.create(
            subject=dataset.id,
            kind=PUBLIC_SERVICE,
            created=datetime.now(),
            created_by=user
        )
        on_badge_added.send(badge)  # Updating metrics.
        dataset.reload()
        self.assertEqual(dataset.metrics['badges'], 1)

        response = self.delete(url_for('api.badge', id=badge.id))
        self.assertStatus(response, 204)

        dataset.reload()
        self.assertEqual(dataset.metrics['badges'], 0)

    def test_remove_badge_without_login(self):
        user = UserFactory()
        organization = Organization.objects.create(
            name='Test organization',
            description='Description'
        )
        badge = OrganizationBadge.objects.create(
            subject=organization.id,
            kind=PUBLIC_SERVICE,
            created=datetime.now(),
            created_by=user
        )
        on_badge_added.send(badge)  # Updating metrics.

        response = self.delete(url_for('api.badge', id=badge.id), {
            'removed': datetime.now(),
            'removed_by': user
        })
        self.assertStatus(response, 401)

        organization.reload()
        self.assertEqual(organization.metrics['badges'], 1)

    def test_remove_badge_permissions(self):
        # The user is not pan Editor or Admin of that organization.
        user = self.login()
        organization = Organization.objects.create(
            name='Test organization',
            description='Description'
        )
        badge = OrganizationBadge.objects.create(
            subject=organization.id,
            kind=PUBLIC_SERVICE,
            created=datetime.now(),
            created_by=user
        )
        on_badge_added.send(badge)  # Updating metrics.

        response = self.delete(url_for('api.badge', id=badge.id), {
            'removed': datetime.now(),
            'removed_by': user
        })
        self.assertStatus(response, 403)

        organization.reload()
        self.assertEqual(organization.metrics['badges'], 1)
