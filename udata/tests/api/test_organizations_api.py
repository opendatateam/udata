# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import url_for

from udata.models import (
    Organization, Member, MembershipRequest, Follow, Issue, Discussion,
    CERTIFIED, PUBLIC_SERVICE
)

from . import APITestCase

from udata.utils import faker
from udata.core.badges.factories import badge_factory
from udata.core.badges.signals import on_badge_added, on_badge_removed
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory, AdminFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory

from udata.tests.helpers import capture_mails, assert_emit, assert_not_emit

import udata.core.badges.tasks  # noqa


class OrganizationAPITest(APITestCase):
    modules = ['core.organization', 'core.user']

    def test_organization_api_list(self):
        '''It should fetch an organization list from the API'''
        with self.autoindex():
            organizations = [OrganizationFactory() for i in range(3)]

        response = self.get(url_for('api.organizations'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(organizations))

    def test_organization_api_get(self):
        '''It should fetch an organization from the API'''
        organization = OrganizationFactory()
        response = self.get(url_for('api.organization', org=organization))
        self.assert200(response)

    def test_organization_api_get_deleted(self):
        '''It should not fetch a deleted organization from the API'''
        organization = OrganizationFactory(deleted=datetime.now())
        response = self.get(url_for('api.organization', org=organization))
        self.assert410(response)

    def test_organization_api_get_deleted_but_authorized(self):
        '''It should fetch a deleted organization from the API if authorized'''
        self.login()
        member = Member(user=self.user, role='editor')
        organization = OrganizationFactory(deleted=datetime.now(),
                                           members=[member])
        response = self.get(url_for('api.organization', org=organization))
        self.assert200(response)

    def test_organization_api_create(self):
        '''It should create an organization from the API'''
        data = OrganizationFactory.as_dict()
        self.login()
        response = self.post(url_for('api.organizations'), data)
        self.assert201(response)
        self.assertEqual(Organization.objects.count(), 1)

        org = Organization.objects.first()
        member = org.member(self.user)
        self.assertIsNotNone(member, 'Current user should be a member')
        self.assertEqual(member.role, 'admin',
                         'Current user should be an administrator')

    def test_dataset_api_update(self):
        '''It should update an organization from the API'''
        self.login()
        member = Member(user=self.user, role='admin')
        org = OrganizationFactory(members=[member])
        data = org.to_dict()
        data['description'] = 'new description'
        response = self.put(url_for('api.organization', org=org), data)
        self.assert200(response)
        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(Organization.objects.first().description,
                         'new description')

    def test_dataset_api_update_deleted(self):
        '''It should not update a deleted organization from the API'''
        org = OrganizationFactory(deleted=datetime.now())
        data = org.to_dict()
        data['description'] = 'new description'
        self.login()
        response = self.put(url_for('api.organization', org=org), data)
        self.assert410(response)
        self.assertEqual(Organization.objects.first().description,
                         org.description)

    def test_dataset_api_update_forbidden(self):
        '''It should not update an organization from the API if not admin'''
        org = OrganizationFactory()
        data = org.to_dict()
        data['description'] = 'new description'
        self.login()
        response = self.put(url_for('api.organization', org=org), data)
        self.assert403(response)
        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(Organization.objects.first().description,
                         org.description)

    def test_organization_api_delete(self):
        '''It should delete an organization from the API'''
        self.login()
        member = Member(user=self.user, role='admin')
        org = OrganizationFactory(members=[member])
        response = self.delete(url_for('api.organization', org=org))
        self.assertStatus(response, 204)
        self.assertEqual(Organization.objects.count(), 1)
        self.assertIsNotNone(Organization.objects[0].deleted)

    def test_organization_api_delete_deleted(self):
        '''It should not delete a deleted organization from the API'''
        self.login()
        organization = OrganizationFactory(deleted=datetime.now())
        response = self.delete(url_for('api.organization', org=organization))
        self.assert410(response)
        self.assertIsNotNone(Organization.objects[0].deleted)

    def test_organization_api_delete_as_editor_forbidden(self):
        '''It should not delete an organization from the API if not admin'''
        self.login()
        member = Member(user=self.user, role='editor')
        org = OrganizationFactory(members=[member])
        response = self.delete(url_for('api.organization', org=org))
        self.assert403(response)
        self.assertEqual(Organization.objects.count(), 1)
        self.assertIsNone(Organization.objects[0].deleted)

    def test_organization_api_delete_as_non_member_forbidden(self):
        '''It should delete an organization from the API if not member'''
        self.login()
        org = OrganizationFactory()
        response = self.delete(url_for('api.organization', org=org))
        self.assert403(response)
        self.assertEqual(Organization.objects.count(), 1)
        self.assertIsNone(Organization.objects[0].deleted)


class MembershipAPITest(APITestCase):
    modules = ['core.user', 'core.organization']

    def test_request_membership(self):
        organization = OrganizationFactory()
        user = self.login()
        data = {'comment': 'a comment'}

        api_url = url_for('api.request_membership', org=organization)
        response = self.post(api_url, data)
        self.assert201(response)

        organization.reload()
        self.assertEqual(len(organization.requests), 1)
        self.assertEqual(len(organization.pending_requests), 1)
        self.assertEqual(len(organization.refused_requests), 0)
        self.assertEqual(len(organization.accepted_requests), 0)

        request = organization.requests[0]
        self.assertEqual(request.user, user)
        self.assertEqual(request.status, 'pending')
        self.assertEqual(request.comment, 'a comment')
        self.assertIsNone(request.handled_on)
        self.assertIsNone(request.handled_by)
        self.assertIsNone(request.refusal_comment)

    def test_request_existing_pending_membership(self):
        user = self.login()
        previous_request = MembershipRequest(user=user, comment='previous')
        organization = OrganizationFactory(requests=[previous_request])
        data = {'comment': 'a comment'}

        api_url = url_for('api.request_membership', org=organization)
        response = self.post(api_url, data)
        self.assert200(response)

        organization.reload()
        self.assertEqual(len(organization.requests), 1)
        self.assertEqual(len(organization.pending_requests), 1)
        self.assertEqual(len(organization.refused_requests), 0)
        self.assertEqual(len(organization.accepted_requests), 0)

        request = organization.requests[0]
        self.assertEqual(request.user, user)
        self.assertEqual(request.status, 'pending')
        self.assertEqual(request.comment, 'a comment')
        self.assertIsNone(request.handled_on)
        self.assertIsNone(request.handled_by)
        self.assertIsNone(request.refusal_comment)

    def test_accept_membership(self):
        user = self.login()
        applicant = UserFactory()
        membership_request = MembershipRequest(user=applicant, comment='test')
        member = Member(user=user, role='admin')
        organization = OrganizationFactory(
            members=[member], requests=[membership_request])

        api_url = url_for(
            'api.accept_membership',
            org=organization,
            id=membership_request.id)
        response = self.post(api_url)
        self.assert200(response)

        self.assertEqual(response.json['role'], 'editor')

        organization.reload()
        self.assertEqual(len(organization.requests), 1)
        self.assertEqual(len(organization.pending_requests), 0)
        self.assertEqual(len(organization.refused_requests), 0)
        self.assertEqual(len(organization.accepted_requests), 1)
        self.assertTrue(organization.is_member(applicant))

        request = organization.requests[0]
        self.assertEqual(request.user, applicant)
        self.assertEqual(request.status, 'accepted')
        self.assertEqual(request.comment, 'test')
        self.assertEqual(request.handled_by, user)
        self.assertIsNotNone(request.handled_on)
        self.assertIsNone(request.refusal_comment)

    def test_accept_membership_404(self):
        user = self.login()
        member = Member(user=user, role='admin')
        organization = OrganizationFactory(members=[member])

        api_url = url_for(
            'api.accept_membership',
            org=organization,
            id=MembershipRequest().id)
        response = self.post(api_url)
        self.assert404(response)

        self.assertEqual(response.json['message'], 'Unknown membership request id')

    def test_refuse_membership(self):
        user = self.login()
        applicant = UserFactory()
        membership_request = MembershipRequest(user=applicant, comment='test')
        member = Member(user=user, role='admin')
        organization = OrganizationFactory(
            members=[member], requests=[membership_request])
        data = {'comment': 'no'}

        api_url = url_for(
            'api.refuse_membership',
            org=organization,
            id=membership_request.id)
        response = self.post(api_url, data)
        self.assert200(response)

        organization.reload()
        self.assertEqual(len(organization.requests), 1)
        self.assertEqual(len(organization.pending_requests), 0)
        self.assertEqual(len(organization.refused_requests), 1)
        self.assertEqual(len(organization.accepted_requests), 0)
        self.assertFalse(organization.is_member(applicant))

        request = organization.requests[0]
        self.assertEqual(request.user, applicant)
        self.assertEqual(request.status, 'refused')
        self.assertEqual(request.comment, 'test')
        self.assertEqual(request.refusal_comment, 'no')
        self.assertEqual(request.handled_by, user)
        self.assertIsNotNone(request.handled_on)

    def test_refuse_membership_404(self):
        user = self.login()
        member = Member(user=user, role='admin')
        organization = OrganizationFactory(members=[member])

        api_url = url_for(
            'api.refuse_membership',
            org=organization,
            id=MembershipRequest().id)
        response = self.post(api_url)
        self.assert404(response)

        self.assertEqual(response.json['message'], 'Unknown membership request id')

    def test_create_member(self):
        user = self.login()
        added_user = UserFactory()
        organization = OrganizationFactory(members=[
            Member(user=user, role='admin'),
        ])

        api_url = url_for('api.member', org=organization, user=added_user)
        response = self.post(api_url, {'role': 'admin'})

        self.assert201(response)

        self.assertEqual(response.json['role'], 'admin')

        organization.reload()
        self.assertTrue(organization.is_member(added_user))
        self.assertTrue(organization.is_admin(added_user))

    def test_create_member_exists(self):
        user = self.login()
        added_user = UserFactory()
        organization = OrganizationFactory(members=[
            Member(user=user, role='admin'),
            Member(user=added_user, role='editor')
        ])

        api_url = url_for('api.member', org=organization, user=added_user)
        response = self.post(api_url, {'role': 'admin'})

        self.assertStatus(response, 409)

        self.assertEqual(response.json['role'], 'editor')

        organization.reload()
        self.assertTrue(organization.is_member(added_user))
        self.assertFalse(organization.is_admin(added_user))

    def test_update_member(self):
        user = self.login()
        updated_user = UserFactory()
        organization = OrganizationFactory(members=[
            Member(user=user, role='admin'),
            Member(user=updated_user, role='editor')
        ])

        api_url = url_for('api.member', org=organization, user=updated_user)
        response = self.put(api_url, {'role': 'admin'})

        self.assert200(response)

        self.assertEqual(response.json['role'], 'admin')

        organization.reload()
        self.assertTrue(organization.is_member(updated_user))
        self.assertTrue(organization.is_admin(updated_user))

    def test_delete_member(self):
        user = self.login()
        deleted_user = UserFactory()
        organization = OrganizationFactory(members=[
            Member(user=user, role='admin'),
            Member(user=deleted_user, role='editor')
        ])

        api_url = url_for('api.member', org=organization, user=deleted_user)
        response = self.delete(api_url)
        self.assert204(response)

        organization.reload()
        self.assertFalse(organization.is_member(deleted_user))

    def test_follow_org(self):
        '''It should follow an organization on POST'''
        user = self.login()
        to_follow = OrganizationFactory()

        response = self.post(
            url_for('api.organization_followers', id=to_follow.id))
        self.assert201(response)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(Follow.objects.followers(to_follow).count(), 1)
        follow = Follow.objects.followers(to_follow).first()
        self.assertIsInstance(follow.following, Organization)
        self.assertEqual(Follow.objects.following(user).count(), 1)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_unfollow_org(self):
        '''It should unfollow the organization on DELETE'''
        user = self.login()
        to_follow = OrganizationFactory()
        Follow.objects.create(follower=user, following=to_follow)

        response = self.delete(
            url_for('api.organization_followers', id=to_follow.id))
        self.assert200(response)

        nb_followers = Follow.objects.followers(to_follow).count()

        self.assertEqual(nb_followers, 0)
        self.assertEqual(response.json['followers'], nb_followers)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(Follow.objects.following(user).count(), 0)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_suggest_organizations_api(self):
        '''It should suggest organizations'''
        with self.autoindex():
            for i in range(4):
                OrganizationFactory(
                    name='test-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.suggest_organizations'),
                            qs={'q': 'tes', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('name', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('image_url', suggestion)
            self.assertIn('acronym', suggestion)
            self.assertTrue(suggestion['name'].startswith('test'))

    def test_suggest_organizations_with_special_chars(self):
        '''It should suggest organizations with special caracters'''
        with self.autoindex():
            for i in range(4):
                OrganizationFactory(
                    name='testé-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.suggest_organizations'),
                            qs={'q': 'testé', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('name', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('image_url', suggestion)
            self.assertTrue(suggestion['name'].startswith('testé'))

    def test_suggest_organizations_with_multiple_words(self):
        '''It should suggest organizations with words'''
        with self.autoindex():
            for i in range(4):
                OrganizationFactory(
                    name='mon testé-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.suggest_organizations'),
                            qs={'q': 'mon testé', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('name', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('image_url', suggestion)
            self.assertTrue(suggestion['name'].startswith('mon testé'))

    def test_suggest_organizations_with_apostrophe(self):
        '''It should suggest organizations with words'''
        with self.autoindex():
            for i in range(4):
                OrganizationFactory(
                    name='Ministère de l\'intérieur {0}'.format(i)
                    if i % 2 else faker.word())

        response = self.get(url_for('api.suggest_organizations'),
                            qs={'q': 'Ministère intérieur', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('name', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('image_url', suggestion)
            self.assertTrue(
                suggestion['name'].startswith('Ministère de l\'intérieur'))

    def test_suggest_organizations_api_no_match(self):
        '''It should not provide organization suggestion if no match'''
        with self.autoindex():
            for i in range(3):
                OrganizationFactory()

        response = self.get(url_for('api.suggest_organizations'),
                            qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_organizations_api_empty(self):
        '''It should not provide organization suggestion if no data'''
        self.init_search()
        response = self.get(url_for('api.suggest_organizations'),
                            qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_organizations_homonyms(self):
        '''It should suggest organizations and not deduplicate homonyms'''
        with self.autoindex():
            OrganizationFactory.create_batch(2, name='homonym')

        response = self.get(url_for('api.suggest_organizations'),
                            qs={'q': 'homonym', 'size': '5'})
        self.assert200(response)

        self.assertEqual(len(response.json), 2)

        for suggestion in response.json:
            self.assertEqual(suggestion['name'], 'homonym')

    def test_suggest_organizations_by_id(self):
        '''It should suggest an organization by its ID'''
        with self.autoindex():
            orgs = OrganizationFactory.create_batch(3)

        first_org = orgs[0]
        response = self.get(url_for('api.suggest_organizations'),
                            qs={'q': str(first_org.id), 'size': '5'})
        self.assert200(response)

        # The batch factory generates ids that might be too close
        # which then are found with the fuzzy search.
        suggested_ids = [u['id'] for u in response.json]
        self.assertGreaterEqual(len(suggested_ids), 1)
        self.assertIn(str(first_org.id), suggested_ids)


class OrganizationDatasetsAPITest(APITestCase):
    modules = ['core.organization', 'core.dataset']

    def test_list_org_datasets(self):
        '''Should list organization datasets'''
        org = OrganizationFactory()
        datasets = DatasetFactory.create_batch(3, organization=org)

        response = self.get(url_for('api.org_datasets', org=org))

        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(datasets))

    def test_list_org_datasets_private(self):
        '''Should include private datasets when member'''
        self.login()
        member = Member(user=self.user, role='admin')
        org = OrganizationFactory(members=[member])
        datasets = DatasetFactory.create_batch(3, organization=org,
                                               private=True)

        response = self.get(url_for('api.org_datasets', org=org))

        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(datasets))

    def test_list_org_datasets_hide_private(self):
        '''Should not include private datasets when not member'''
        org = OrganizationFactory()
        datasets = DatasetFactory.create_batch(3, organization=org)
        DatasetFactory.create_batch(2, organization=org, private=True)

        response = self.get(url_for('api.org_datasets', org=org))

        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(datasets))

    def test_list_org_datasets_with_size(self):
        '''Should list organization datasets'''
        org = OrganizationFactory()
        DatasetFactory.create_batch(3, organization=org)

        response = self.get(
            url_for('api.org_datasets', org=org), qs={'page_size': 2})

        self.assert200(response)
        self.assertEqual(len(response.json['data']), 2)


class OrganizationReusesAPITest(APITestCase):
    modules = ['core.organization', 'core.reuse']

    def test_list_org_reuses(self):
        '''Should list organization reuses'''
        org = OrganizationFactory()
        reuses = ReuseFactory.create_batch(3, organization=org)

        response = self.get(url_for('api.org_reuses', org=org))

        self.assert200(response)
        self.assertEqual(len(response.json), len(reuses))

    def test_list_org_reuses_private(self):
        '''Should include private reuses when member'''
        self.login()
        member = Member(user=self.user, role='admin')
        org = OrganizationFactory(members=[member])
        reuses = ReuseFactory.create_batch(3, organization=org, private=True)

        response = self.get(url_for('api.org_reuses', org=org))

        self.assert200(response)
        self.assertEqual(len(response.json), len(reuses))

    def test_list_org_reuses_hide_private(self):
        '''Should not include private reuses when not member'''
        org = OrganizationFactory()
        reuses = ReuseFactory.create_batch(3, organization=org)
        ReuseFactory.create_batch(2, organization=org, private=True)

        response = self.get(url_for('api.org_reuses', org=org))

        self.assert200(response)
        self.assertEqual(len(response.json), len(reuses))


class OrganizationIssuesAPITest(APITestCase):
    modules = ['core.user']

    def test_list_org_issues(self):
        '''Should list organization issues'''
        user = UserFactory()
        org = OrganizationFactory()
        reuse = ReuseFactory(organization=org)
        dataset = DatasetFactory(organization=org)
        issues = [
            Issue.objects.create(subject=dataset, title='', user=user),
            Issue.objects.create(subject=reuse, title='', user=user)
        ]

        # Should not be listed
        Issue.objects.create(subject=DatasetFactory(), title='', user=user)
        Issue.objects.create(subject=ReuseFactory(), title='', user=user)

        response = self.get(url_for('api.org_issues', org=org))

        self.assert200(response)
        self.assertEqual(len(response.json), len(issues))

        issues_ids = [str(i.id) for i in issues]
        for issue in response.json:
            self.assertIn(issue['id'], issues_ids)


class OrganizationDiscussionsAPITest(APITestCase):
    modules = ['core.user']

    def test_list_org_discussions(self):
        '''Should list organization discussions'''
        user = UserFactory()
        org = OrganizationFactory()
        reuse = ReuseFactory(organization=org)
        dataset = DatasetFactory(organization=org)
        discussions = [
            Discussion.objects.create(subject=dataset, title='', user=user),
            Discussion.objects.create(subject=reuse, title='', user=user)
        ]

        # Should not be listed
        Issue.objects.create(subject=DatasetFactory(), title='', user=user)
        Issue.objects.create(subject=ReuseFactory(), title='', user=user)

        response = self.get(url_for('api.org_discussions', org=org))

        self.assert200(response)
        self.assertEqual(len(response.json), len(discussions))

        discussions_ids = [str(d.id) for d in discussions]
        for discussion in response.json:
            self.assertIn(discussion['id'], discussions_ids)


class OrganizationBadgeAPITest(APITestCase):
    modules = ['core.user', 'core.organization']

    @classmethod
    def setUpClass(cls):
        # Register at least two badges
        Organization.__badges__['test-1'] = 'Test 1'
        Organization.__badges__['test-2'] = 'Test 2'

        cls.factory = badge_factory(Organization)

    def setUp(self):
        self.login(AdminFactory())
        self.organization = OrganizationFactory()

    def test_list(self):
        response = self.get(url_for('api.available_organization_badges'))
        self.assertStatus(response, 200)
        self.assertEqual(len(response.json), len(Organization.__badges__))
        for kind, label in Organization.__badges__.items():
            self.assertIn(kind, response.json)
            self.assertEqual(response.json[kind], label)

    def test_create(self):
        data = self.factory.as_dict()
        url = url_for('api.organization_badges', org=self.organization)
        with self.api_user(), assert_emit(on_badge_added):
            response = self.post(url, data)
        self.assert201(response)
        self.organization.reload()
        self.assertEqual(len(self.organization.badges), 1)

    def test_create_badge_certified_mail(self):
        member = Member(user=self.user, role='admin')
        org = OrganizationFactory(members=[member])

        data = self.factory.as_dict()
        data['kind'] = CERTIFIED

        with capture_mails() as mails:
            self.post(
                url_for('api.organization_badges', org=org),
                data)

        # Should have sent one mail to each member of organization
        members_emails = [m.user.email for m in org.members]
        self.assertEqual(len(mails), len(members_emails))
        self.assertListEqual([m.recipients[0] for m in mails], members_emails)

    def test_create_badge_public_service_mail(self):
        member = Member(user=self.user, role='admin')
        org = OrganizationFactory(members=[member])

        data = self.factory.as_dict()
        data['kind'] = PUBLIC_SERVICE

        with capture_mails() as mails:
            self.post(
                url_for('api.organization_badges', org=org),
                data)
            # do it a second time, no email expected for this one
            self.post(
                url_for('api.organization_badges', org=self.organization),
                data)

        # Should have sent one mail to each member of organization
        members_emails = [m.user.email for m in org.members]
        self.assertEqual(len(mails), len(members_emails))
        self.assertListEqual([m.recipients[0] for m in mails], members_emails)

    def test_create_same(self):
        data = self.factory.as_dict()
        url = url_for('api.organization_badges', org=self.organization)
        with self.api_user():
            with assert_emit(on_badge_added):
                self.post(url, data)
            with assert_not_emit(on_badge_added):
                response = self.post(url, data)
        self.assertStatus(response, 200)
        self.organization.reload()
        self.assertEqual(len(self.organization.badges), 1)

    def test_create_2nd(self):
        # Explicitely setting the kind to avoid collisions given the
        # small number of choices for kinds.
        kinds_keys = Organization.__badges__.keys()
        self.organization.badges.append(
            self.factory(kind=kinds_keys[0]))
        self.organization.save()
        data = self.factory.as_dict()
        data['kind'] = kinds_keys[1]
        with self.api_user():
            response = self.post(
                url_for('api.organization_badges', org=self.organization),
                data)
        self.assert201(response)
        self.organization.reload()
        self.assertEqual(len(self.organization.badges), 2)

    def test_delete(self):
        badge = self.factory()
        self.organization.badges.append(badge)
        self.organization.save()
        url = url_for('api.organization_badge',
                      org=self.organization,
                      badge_kind=str(badge.kind))
        with self.api_user():
            with assert_emit(on_badge_removed):
                response = self.delete(url)
        self.assertStatus(response, 204)
        self.organization.reload()
        self.assertEqual(len(self.organization.badges), 0)

    def test_delete_404(self):
        with self.api_user():
            response = self.delete(
                url_for('api.organization_badge', org=self.organization,
                        badge_kind=str(self.factory().kind)))
        self.assert404(response)
