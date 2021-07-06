from datetime import datetime

from flask import url_for

from udata.models import Discussion, Follow, Issue, Member, User
from udata.core.discussions.models import Message as DiscMsg
from udata.core.issues.models import Message as IssueMsg
from udata.core.dataset.factories import (
    CommunityResourceFactory,
    DatasetFactory,
    VisibleDatasetFactory,
)
from udata.core.dataset.activities import UserCreatedDataset
from udata.core.discussions.factories import DiscussionFactory
from udata.core.issues.factories import IssueFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.i18n import _
from udata.tests.helpers import capture_mails
from udata.utils import faker

from . import APITestCase


class MeAPITest(APITestCase):
    modules = []

    def test_get_profile(self):
        '''It should fetch my user data on GET'''
        self.login()
        response = self.get(url_for('api.me'))
        self.assert200(response)
        self.assertEqual(response.json['email'], self.user.email)
        self.assertEqual(response.json['first_name'], self.user.first_name)
        self.assertEqual(response.json['roles'], [])

    def test_get_profile_with_deleted_org(self):
        '''It should not display my membership to deleted organizations'''
        user = self.login()
        member = Member(user=user, role='editor')
        org = OrganizationFactory(members=[member])
        deleted_org = OrganizationFactory(members=[member],
                                          deleted=datetime.now())
        response = self.get(url_for('api.me'))
        self.assert200(response)
        orgs = [o['id'] for o in response.json['organizations']]
        self.assertIn(str(org.id), orgs)
        self.assertNotIn(str(deleted_org.id), orgs)

    def test_get_profile_401(self):
        '''It should raise a 401 on GET /me if no user is authenticated'''
        response = self.get(url_for('api.me'))
        self.assert401(response)

    def test_update_profile(self):
        '''It should update my profile from the API'''
        self.login()
        data = self.user.to_dict()
        self.assertTrue(self.user.active)
        data['about'] = 'new about'
        data['active'] = False
        response = self.put(url_for('api.me'), data)
        self.assert200(response)
        self.assertEqual(User.objects.count(), 1)
        self.user.reload()
        self.assertEqual(self.user.about, 'new about')
        self.assertTrue(self.user.active)

    def test_my_metrics(self):
        self.login()
        response = self.get(url_for('api.my_metrics'))
        self.assert200(response)
        self.assertEqual(response.json['resources_availability'], 100.)
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
            VisibleDatasetFactory(owner=user, title='foô'),
        ]
        org_datasets = [
            VisibleDatasetFactory(organization=organization, title='foô'),
        ]

        # Should not be listed.
        VisibleDatasetFactory(owner=user)
        VisibleDatasetFactory(organization=organization)

        response = self.get(url_for('api.my_org_datasets'),
                            qs={'q': 'foô'})
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
            CommunityResourceFactory(owner=user, title='foô'),
        ]
        org_community_resources = [
            CommunityResourceFactory(organization=organization, title='foô'),
        ]

        # Should not be listed.
        CommunityResourceFactory(owner=user)
        CommunityResourceFactory(organization=organization)

        response = self.get(url_for('api.my_org_community_resources'),
                            qs={'q': 'foô'})
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
            ReuseFactory(owner=user, title='foô'),
        ]
        org_reuses = [
            ReuseFactory(organization=organization, title='foô'),
        ]

        # Should not be listed.
        ReuseFactory(owner=user)
        ReuseFactory(organization=organization)

        response = self.get(url_for('api.my_org_reuses'), qs={'q': 'foô'})
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
            Issue.objects.create(subject=s, title='', user=sender)
            for s in (dataset, org_dataset, reuse, org_reuse)
        ]

        # Should not be listed
        Issue.objects.create(subject=VisibleDatasetFactory(), title='', user=sender)
        Issue.objects.create(subject=ReuseFactory(), title='', user=sender)

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
            Issue.objects.create(subject=org_dataset, title='foô', user=user),
            Issue.objects.create(subject=reuse, title='foô', user=user),
        ]

        # Should not be listed.
        Issue.objects.create(subject=dataset, title='', user=user),
        Issue.objects.create(subject=org_reuse, title='', user=user),

        # Should really not be listed.
        Issue.objects.create(subject=VisibleDatasetFactory(), title='', user=user)
        Issue.objects.create(subject=ReuseFactory(), title='', user=user)

        response = self.get(url_for('api.my_org_issues'), qs={'q': 'foô'})
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
            Discussion.objects.create(subject=dataset, title='', user=user),
            Discussion.objects.create(subject=org_dataset, title='', user=user),
            Discussion.objects.create(subject=reuse, title='', user=user),
            Discussion.objects.create(subject=org_reuse, title='', user=user),
        ]

        # Should not be listed
        Discussion.objects.create(subject=VisibleDatasetFactory(), title='', user=user)
        Discussion.objects.create(subject=ReuseFactory(), title='', user=user)

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
            Discussion.objects.create(subject=dataset, title='foô', user=user),
            Discussion.objects.create(subject=org_reuse, title='foô', user=user),
        ]

        # Should not be listed.
        Discussion.objects.create(subject=reuse, title='', user=user),
        Discussion.objects.create(subject=org_dataset, title='', user=user),

        # Should really not be listed.
        Discussion.objects.create(subject=VisibleDatasetFactory(), title='foô', user=user)
        Discussion.objects.create(subject=ReuseFactory(), title='foô', user=user)

        response = self.get(url_for('api.my_org_discussions'), qs={'q': 'foô'})
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
        self.assertFalse(self.user.apikey.startswith("b'"))
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

    def test_delete(self):
        '''It should delete the connected user'''
        user = self.login()
        self.assertIsNone(user.deleted)
        other_user = UserFactory()
        members = [Member(user=user), Member(user=other_user)]
        organization = OrganizationFactory(members=members)
        disc_msg_content = faker.sentence()
        disc_msg = DiscMsg(content=disc_msg_content,
                           posted_by=user)
        other_disc_msg_content = faker.sentence()
        other_disc_msg = DiscMsg(content=other_disc_msg_content,
                                 posted_by=other_user)
        discussion = DiscussionFactory(user=user,
                                       discussion=[disc_msg, other_disc_msg])
        issue_msg_content = faker.sentence()
        issue_msg = IssueMsg(content=issue_msg_content,
                             posted_by=user)
        other_issue_msg_content = faker.sentence()
        other_issue_msg = IssueMsg(content=other_issue_msg_content,
                                   posted_by=other_user)
        issue = IssueFactory(user=user,
                             discussion=[issue_msg, other_issue_msg])
        dataset = DatasetFactory(owner=user)
        reuse = ReuseFactory(owner=user)
        resource = CommunityResourceFactory(owner=user)
        activity = UserCreatedDataset.objects().create(actor=user, related_to=dataset)

        following = Follow.objects().create(follower=user, following=other_user)
        followed = Follow.objects().create(follower=other_user, following=user)

        with capture_mails() as mails:
            response = self.delete(url_for('api.me'))
        self.assertEqual(len(mails), 1)
        self.assertEqual(mails[0].send_to, set([user.email]))
        self.assertEqual(mails[0].subject, _('Account deletion'))
        self.assert204(response)

        user.reload()
        organization.reload()
        discussion.reload()
        issue.reload()
        dataset.reload()
        reuse.reload()
        resource.reload()
        activity.reload()

        # The following are deleted
        with self.assertRaises(Follow.DoesNotExist):
            following.reload()
        # The followers are deleted
        with self.assertRaises(Follow.DoesNotExist):
            followed.reload()

        # The personal data of the user are anonymized
        self.assertEqual(user.email, '{}@deleted'.format(user.id))
        self.assertEqual(user.password, None)
        self.assertEqual(user.active, False)
        self.assertEqual(user.first_name, 'DELETED')
        self.assertEqual(user.last_name, 'DELETED')
        self.assertFalse(bool(user.avatar))
        self.assertEqual(user.avatar_url, None)
        self.assertEqual(user.website, None)
        self.assertEqual(user.about, None)

        # The user is marked as deleted
        self.assertIsNotNone(user.deleted)

        # The user is removed from his organizations
        self.assertEqual(len(organization.members), 1)
        self.assertEqual(organization.members[0].user.id, other_user.id)

        # The discussions are kept but the messages are anonymized
        self.assertEqual(len(discussion.discussion), 2)
        self.assertEqual(discussion.discussion[0].content, 'DELETED')
        self.assertEqual(discussion.discussion[1].content,
                         other_disc_msg_content)

        # The issues are kept and the messages are not anonymized
        self.assertEqual(len(issue.discussion), 2)
        self.assertEqual(issue.discussion[0].content, issue_msg_content)
        self.assertEqual(issue.discussion[1].content,
                         other_issue_msg_content)

        # The datasets are unchanged
        self.assertEqual(dataset.owner, user)

        # The reuses are unchanged
        self.assertEqual(reuse.owner, user)

        # The community resources are unchanged
        self.assertEqual(resource.owner, user)

        # The activities are unchanged
        self.assertEqual(activity.actor, user)
