# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import (
    DatasetIssue, DatasetDiscussion, ReuseIssue, ReuseDiscussion, Member, User
)

from udata.tests.factories import (
    CommunityResourceFactory, VisibleDatasetFactory, OrganizationFactory,
    ReuseFactory, UserFactory
)

from . import APITestCase


class MeAPITest(APITestCase):
    def test_get_profile(self):
        '''It should fetch my user data on GET'''
        self.login()
        response = self.get(url_for('api.me'))
        self.assert200(response)
        # self.assertEqual(response.json['email'], self.user.email)
        self.assertEqual(response.json['first_name'], self.user.first_name)
        self.assertEqual(response.json['roles'], [])

    def test_get_profile_401(self):
        '''It should raise a 401 on GET /me if no user is authenticated'''
        response = self.get(url_for('api.me'))
        self.assert401(response)

    def test_update_profile(self):
        '''It should update my profile from the API'''
        self.login()
        data = self.user.to_dict()
        data['about'] = 'new about'
        response = self.put(url_for('api.me'), data)
        self.assert200(response)
        self.assertEqual(User.objects.count(), 1)
        self.user.reload()
        self.assertEqual(self.user.about, 'new about')

    def test_my_metrics(self):
        self.login()
        response = self.get(url_for('api.my_metrics'))
        self.assert200(response)
        self.assertEqual(response.json['resources_availability'], 0)
        self.assertEqual(response.json['datasets_org_count'], 0)
        self.assertEqual(response.json['followers_org_count'], 0)
        self.assertEqual(response.json['datasets_count'], 0)
        self.assertEqual(response.json['followers_count'], 0)

    def test_my_reuses(self):
        user = self.login()
        reuses = [ReuseFactory(owner=user) for _ in range(2)]

        response = self.get(url_for('api.my_reuses'))
        self.assert200(response)

        self.assertEqual(len(response.json), len(reuses))

    def test_my_org_datasets(self):
        user = self.login()
        member = Member(user=user, role='editor')
        organization = OrganizationFactory(members=[member])
        community_resources = [
            VisibleDatasetFactory(owner=user) for _ in range(2)]
        org_datasets = [
            VisibleDatasetFactory(organization=organization)
            for _ in range(2)]

        response = self.get(url_for('api.my_org_datasets'))
        self.assert200(response)
        self.assertEqual(
            len(response.json),
            len(community_resources) + len(org_datasets))

    def test_my_org_datasets_with_search(self):
        user = self.login()
        member = Member(user=user, role='editor')
        organization = OrganizationFactory(members=[member])
        datasets = [
            VisibleDatasetFactory(owner=user, title='foo'),
        ]
        org_datasets = [
            VisibleDatasetFactory(organization=organization, title='foo'),
        ]

        # Should not be listed.
        VisibleDatasetFactory(owner=user)
        VisibleDatasetFactory(organization=organization)

        response = self.get(url_for('api.my_org_datasets'),
                            qs={'q': 'foo'})
        self.assert200(response)
        self.assertEqual(len(response.json), len(datasets) + len(org_datasets))

    def test_my_org_community_resources(self):
        user = self.login()
        member = Member(user=user, role='editor')
        organization = OrganizationFactory(members=[member])
        community_resources = [
            CommunityResourceFactory(owner=user) for _ in range(2)]
        org_community_resources = [
            CommunityResourceFactory(organization=organization)
            for _ in range(2)]

        response = self.get(url_for('api.my_org_community_resources'))
        self.assert200(response)
        self.assertEqual(
            len(response.json),
            len(community_resources) + len(org_community_resources))

    def test_my_org_community_resources_with_search(self):
        user = self.login()
        member = Member(user=user, role='editor')
        organization = OrganizationFactory(members=[member])
        community_resources = [
            CommunityResourceFactory(owner=user, title='foo'),
        ]
        org_community_resources = [
            CommunityResourceFactory(organization=organization, title='foo'),
        ]

        # Should not be listed.
        CommunityResourceFactory(owner=user)
        CommunityResourceFactory(organization=organization)

        response = self.get(url_for('api.my_org_community_resources'),
                            qs={'q': 'foo'})
        self.assert200(response)
        self.assertEqual(
            len(response.json),
            len(community_resources) + len(org_community_resources))

    def test_my_org_reuses(self):
        user = self.login()
        member = Member(user=user, role='editor')
        organization = OrganizationFactory(members=[member])
        reuses = [ReuseFactory(owner=user) for _ in range(2)]
        org_reuses = [ReuseFactory(organization=organization)
                      for _ in range(2)]

        response = self.get(url_for('api.my_org_reuses'))
        self.assert200(response)
        self.assertEqual(len(response.json), len(reuses) + len(org_reuses))

    def test_my_org_reuses_with_search(self):
        user = self.login()
        member = Member(user=user, role='editor')
        organization = OrganizationFactory(members=[member])
        reuses = [
            ReuseFactory(owner=user, title='foo'),
        ]
        org_reuses = [
            ReuseFactory(organization=organization, title='foo'),
        ]

        # Should not be listed.
        ReuseFactory(owner=user)
        ReuseFactory(organization=organization)

        response = self.get(url_for('api.my_org_reuses'), qs={'q': 'foo'})
        self.assert200(response)
        self.assertEqual(len(response.json), len(reuses) + len(org_reuses))

    def test_my_org_issues(self):
        user = self.login()
        member = Member(user=user, role='editor')
        organization = OrganizationFactory(members=[member])
        reuse = ReuseFactory(owner=user)
        org_reuse = ReuseFactory(organization=organization)
        dataset = VisibleDatasetFactory(owner=user)
        org_dataset = VisibleDatasetFactory(organization=organization)

        sender = UserFactory()
        issues = [
            DatasetIssue.objects.create(subject=s, title='', user=sender)
            for s in (dataset, org_dataset)
        ] + [
            ReuseIssue.objects.create(subject=s, title='', user=sender)
            for s in (reuse, org_reuse)
        ]

        # Should not be listed
        DatasetIssue.objects.create(
            subject=VisibleDatasetFactory(), title='', user=sender)
        ReuseIssue.objects.create(subject=ReuseFactory(),
                                  title='',
                                  user=sender)

        response = self.get(url_for('api.my_org_issues'))
        self.assert200(response)
        self.assertEqual(len(response.json), len(issues))

    def test_my_org_issues_with_search(self):
        user = self.login()
        member = Member(user=user, role='editor')
        organization = OrganizationFactory(members=[member])
        reuse = ReuseFactory(owner=user)
        org_reuse = ReuseFactory(organization=organization)
        dataset = VisibleDatasetFactory(owner=user)
        org_dataset = VisibleDatasetFactory(organization=organization)

        issues = [
            DatasetIssue.objects.create(
                subject=org_dataset, title='foo', user=user),
            ReuseIssue.objects.create(subject=reuse, title='foo', user=user),
        ]

        # Should not be listed.
        DatasetIssue.objects.create(subject=dataset, title='', user=user),
        ReuseIssue.objects.create(subject=org_reuse, title='', user=user),

        # Should really not be listed.
        DatasetIssue.objects.create(
            subject=VisibleDatasetFactory(), title='', user=user)
        ReuseIssue.objects.create(subject=ReuseFactory(), title='', user=user)

        response = self.get(url_for('api.my_org_issues'), qs={'q': 'foo'})
        self.assert200(response)
        self.assertEqual(len(response.json), len(issues))

    def test_my_org_discussions(self):
        user = self.login()
        member = Member(user=user, role='editor')
        organization = OrganizationFactory(members=[member])
        reuse = ReuseFactory(owner=user)
        org_reuse = ReuseFactory(organization=organization)
        dataset = VisibleDatasetFactory(owner=user)
        org_dataset = VisibleDatasetFactory(organization=organization)

        discussions = [
            DatasetDiscussion.objects.create(
                subject=dataset, title='', user=user),
            DatasetDiscussion.objects.create(
                subject=org_dataset, title='', user=user),
            ReuseDiscussion.objects.create(subject=reuse, title='', user=user),
            ReuseDiscussion.objects.create(
                subject=org_reuse, title='', user=user),
        ]

        # Should not be listed
        DatasetDiscussion.objects.create(
            subject=VisibleDatasetFactory(), title='', user=user)
        ReuseDiscussion.objects.create(
            subject=ReuseFactory(), title='', user=user)

        response = self.get(url_for('api.my_org_discussions'))
        self.assert200(response)
        self.assertEqual(len(response.json), len(discussions))

    def test_my_org_discussions_with_search(self):
        user = self.login()
        member = Member(user=user, role='editor')
        organization = OrganizationFactory(members=[member])
        reuse = ReuseFactory(owner=user)
        org_reuse = ReuseFactory(organization=organization)
        dataset = VisibleDatasetFactory(owner=user)
        org_dataset = VisibleDatasetFactory(organization=organization)

        discussions = [
            DatasetDiscussion.objects.create(
                subject=dataset, title='foo', user=user),
            ReuseDiscussion.objects.create(
                subject=org_reuse, title='foo', user=user),
        ]

        # Should not be listed.
        ReuseDiscussion.objects.create(subject=reuse, title='', user=user),
        DatasetDiscussion.objects.create(
            subject=org_dataset, title='', user=user),

        # Should really not be listed.
        DatasetDiscussion.objects.create(
            subject=VisibleDatasetFactory(), title='foo', user=user)
        ReuseDiscussion.objects.create(
            subject=ReuseFactory(), title='foo', user=user)

        response = self.get(url_for('api.my_org_discussions'), qs={'q': 'foo'})
        self.assert200(response)
        self.assertEqual(len(response.json), len(discussions))

    def test_my_reuses_401(self):
        response = self.get(url_for('api.my_reuses'))
        self.assert401(response)

    def test_generate_apikey(self):
        '''It should generate an API Key on POST'''
        self.login()
        response = self.post(url_for('api.my_apikey'))
        self.assert201(response)
        self.assertIsNotNone(response.json['apikey'])

        self.user.reload()
        self.assertIsNotNone(self.user.apikey)
        self.assertEqual(self.user.apikey, response.json['apikey'])

    def test_regenerate_apikey(self):
        '''It should regenerate an API Key on POST'''
        self.login()
        self.user.generate_api_key()
        self.user.save()

        apikey = self.user.apikey
        response = self.post(url_for('api.my_apikey'))
        self.assert201(response)
        self.assertIsNotNone(response.json['apikey'])

        self.user.reload()
        self.assertIsNotNone(self.user.apikey)
        self.assertNotEqual(self.user.apikey, apikey)
        self.assertEqual(self.user.apikey, response.json['apikey'])

    def test_clear_apikey(self):
        '''It should clear an API Key on DELETE'''
        self.login()
        self.user.generate_api_key()
        self.user.save()

        response = self.delete(url_for('api.my_apikey'))
        self.assert204(response)

        self.user.reload()
        self.assertIsNone(self.user.apikey)
