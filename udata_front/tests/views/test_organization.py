import pytest
from io import StringIO
from datetime import datetime

from flask import url_for

from udata.models import (
    Organization, Member, Follow, CERTIFIED, PUBLIC_SERVICE
)

from udata.frontend import csv
from udata.core.badges.factories import badge_factory

from udata.core.reuse.factories import ReuseFactory, VisibleReuseFactory
from udata.core.dataset.factories import DatasetFactory, VisibleDatasetFactory, ResourceFactory
from udata.core.discussions.factories import DiscussionFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory, AdminFactory

from udata.tests.helpers import capture_mails, assert_starts_with

from udata_front.tests import GouvFrSettings
from udata_front.tests.frontend import GouvfrFrontTestCase
from udata_front.views.organization import OrganizationDetailView

pytestmark = [
    pytest.mark.usefixtures('clean_db'),
]


class OrganizationBlueprintTest(GouvfrFrontTestCase):
    settings = GouvFrSettings
    modules = ['admin']

    def test_render_display(self):
        '''It should render the organization page'''
        organization = OrganizationFactory(description='* Title 1\n* Title 2', )
        url = url_for('organizations.show', org=organization)
        response = self.get(url)
        self.assert200(response)
        self.assertNotIn(b'<meta name="robots" content="noindex, nofollow">',
                         response.data)
        json_ld = self.get_json_ld(response)
        self.assertEqual(json_ld['@context'], 'http://schema.org')
        self.assertEqual(json_ld['@type'], 'Organization')
        self.assertEqual(json_ld['alternateName'], organization.slug)
        self.assertEqual(json_ld['url'], 'http://local.test{}'.format(url))
        self.assertEqual(json_ld['name'], organization.name)
        self.assertEqual(json_ld['description'], 'Title 1 Title 2')

    def test_render_display_if_deleted(self):
        '''It should not render the organization page if deleted'''
        organization = OrganizationFactory(deleted=datetime.now())
        response = self.get(url_for('organizations.show', org=organization))
        self.assert410(response)

    def test_render_display_if_deleted_but_authorized(self):
        '''It should render the organization page if deleted but user can'''
        self.login()
        member = Member(user=self.user, role='editor')
        organization = OrganizationFactory(deleted=datetime.now(),
                                           members=[member])
        response = self.get(url_for('organizations.show', org=organization))
        self.assert200(response)

    def test_render_display_with_datasets(self):
        '''It should render the organization page with some datasets'''
        organization = OrganizationFactory()
        datasets = [
            VisibleDatasetFactory(organization=organization) for _ in range(3)]
        response = self.get(url_for('organizations.show', org=organization))

        self.assert200(response)
        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets), len(datasets))

    def test_render_display_with_private_assets_only_member(self):
        '''It should render the organization page without private and empty assets'''
        organization = OrganizationFactory()
        datasets = [VisibleDatasetFactory(organization=organization)
                    for _ in range(2)]
        reuses = [VisibleReuseFactory(organization=organization)
                  for _ in range(2)]
        for _ in range(2):
            DatasetFactory(organization=organization, resources=[])  # Empty asset
            VisibleDatasetFactory(organization=organization, private=True)
            ReuseFactory(organization=organization, datasets=[])  # Empty asset
            VisibleReuseFactory(organization=organization, private=True)
        response = self.get(url_for('organizations.show', org=organization))

        self.assert200(response)

        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets), len(datasets))

        rendered_reuses = self.get_context_variable('reuses')
        self.assertEqual(len(rendered_reuses), len(reuses))

        rendered_private_datasets = [dataset for dataset in rendered_datasets if dataset.private]
        self.assertEqual(len(rendered_private_datasets), 0)

        rendered_private_reuses = [reuse for reuse in rendered_reuses if reuse.private]
        self.assertEqual(len(rendered_private_reuses), 0)

        total_datasets = self.get_context_variable('total_datasets')
        self.assertEqual(total_datasets, len(datasets))

        total_reuses = self.get_context_variable('total_reuses')
        self.assertEqual(total_reuses, len(reuses))

    def test_render_display_with_private_datasets(self):
        '''It should render the organization page with some private datasets'''
        me = self.login()
        member = Member(user=me, role='editor')
        organization = OrganizationFactory(members=[member])
        # We show paginated datasets on the organisation page
        # so rendered_datasets length will be at most 4
        datasets = [
            VisibleDatasetFactory(organization=organization) for _ in range(2)]
        empty_datasets = [
            DatasetFactory(organization=organization, resources=[]) for _ in range(1)]
        private_datasets = [
            VisibleDatasetFactory(organization=organization, private=True)
            for _ in range(1)]
        response = self.get(url_for('organizations.show', org=organization))

        self.assert200(response)
        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets),
                         len(datasets) + len(private_datasets) + len(empty_datasets))

        rendered_private_datasets = [dataset for dataset in rendered_datasets if dataset.private]
        self.assertEqual(len(rendered_private_datasets), len(private_datasets))

        total_datasets = self.get_context_variable('total_datasets')
        self.assertEqual(total_datasets,
                         len(datasets) + len(private_datasets) + len(empty_datasets))

    def test_render_display_with_paginated_datasets(self):
        '''It should render the organization page with paginated datasets'''
        organization = OrganizationFactory()
        datasets_len = OrganizationDetailView.page_size + 1
        for _ in range(datasets_len):
            VisibleDatasetFactory(organization=organization)
        response = self.get(url_for('organizations.show', org=organization))

        self.assert200(response)
        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets), OrganizationDetailView.page_size)

    def test_render_display_with_paginated_datasets_on_second_page(self):
        '''It should render the organization page with paginated datasets'''
        organization = OrganizationFactory()
        second_page_len = 1
        datasets_len = OrganizationDetailView.page_size + second_page_len
        for _ in range(datasets_len):
            VisibleDatasetFactory(organization=organization)
        response = self.get(url_for('organizations.show', org=organization, datasets_page=2))

        self.assert200(response)
        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets), second_page_len)

    def test_render_display_with_reuses(self):
        '''It should render the organization page with some reuses'''
        organization = OrganizationFactory()
        reuses = [
            VisibleReuseFactory(organization=organization) for _ in range(3)]
        response = self.get(url_for('organizations.show', org=organization))

        self.assert200(response)
        rendered_reuses = self.get_context_variable('reuses')
        self.assertEqual(len(rendered_reuses), len(reuses))

    def test_render_display_with_private_reuses(self):
        '''It should render the organization page with some private reuses'''
        me = self.login()
        member = Member(user=me, role='editor')
        organization = OrganizationFactory(members=[member])
        # We show paginated reuses on the organisation page
        # so rendered_reuses length will be at most 4
        reuses = [VisibleReuseFactory(organization=organization) for _ in range(2)]
        empty_reuses = [
            ReuseFactory(organization=organization, datasets=[]) for _ in range(1)]
        private_reuses = [
            VisibleReuseFactory(organization=organization, private=True)
            for _ in range(1)]
        response = self.get(url_for('organizations.show', org=organization))

        self.assert200(response)
        rendered_reuses = self.get_context_variable('reuses')
        self.assertEqual(len(rendered_reuses),
                         len(reuses) + len(private_reuses) + len(empty_reuses))

        rendered_private_reuses = [reuse for reuse in rendered_reuses if reuse.private]
        self.assertEqual(len(rendered_private_reuses), len(private_reuses))

        total_reuses = self.get_context_variable('total_reuses')
        self.assertEqual(total_reuses, len(reuses) + len(private_reuses) + len(empty_reuses))

    def test_render_display_with_paginated_reuses(self):
        '''It should render the organization page with paginated reuses'''
        organization = OrganizationFactory()
        reuses_len = OrganizationDetailView.page_size + 1
        for _ in range(reuses_len):
            VisibleReuseFactory(organization=organization)
        response = self.get(url_for('organizations.show', org=organization))

        self.assert200(response)
        rendered_reuses = self.get_context_variable('reuses')
        self.assertEqual(len(rendered_reuses), OrganizationDetailView.page_size)

    def test_render_display_with_paginated_reuses_on_second_page(self):
        '''It should render the organization page with paginated datasets'''
        second_page_len = 1
        reuses_len = OrganizationDetailView.page_size + second_page_len
        organization = OrganizationFactory()
        for _ in range(reuses_len):
            VisibleReuseFactory(organization=organization)
        response = self.get(url_for('organizations.show', org=organization, reuses_page=2))

        self.assert200(response)
        rendered_reuses = self.get_context_variable('reuses')
        self.assertEqual(len(rendered_reuses), second_page_len)

    def test_render_display_with_followers(self):
        '''It should render the organization page with followers'''
        org = OrganizationFactory()
        followers = [
            Follow.objects.create(follower=UserFactory(), following=org)
            for _ in range(3)]

        response = self.get(url_for('organizations.show', org=org))
        self.assert200(response)

        rendered_followers = self.get_context_variable('followers')
        self.assertEqual(len(rendered_followers), len(followers))

    def test_not_found(self):
        '''It should render the organization page'''
        response = self.get(url_for('organizations.show', org='not-found'))
        self.assert404(response)

    def test_no_index_on_empty(self):
        '''It should prevent crawlers from indexing empty organizations'''
        organization = OrganizationFactory()
        url = url_for('organizations.show', org=organization)
        response = self.get(url)
        self.assert200(response)
        self.assertIn(b'<meta name="robots" content="noindex, nofollow"',
                      response.data)

    def test_datasets_csv(self):
        org = OrganizationFactory()
        [
            DatasetFactory(organization=org, resources=[ResourceFactory()])
            for _ in range(3)]

        response = self.get(url_for('organizations.datasets_csv', org=org))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO(response.data.decode('utf-8'))
        reader = csv.get_reader(csvfile)
        header = next(reader)

        self.assertEqual(header[0], 'id')
        self.assertIn('title', header)
        self.assertIn('url', header)
        self.assertIn('description', header)
        self.assertIn('created_at', header)
        self.assertIn('last_modified', header)
        self.assertIn('tags', header)
        self.assertIn('metric.reuses', header)

    def test_resources_csv(self):
        org = OrganizationFactory()
        datasets = [
            DatasetFactory(
                organization=org,
                resources=[ResourceFactory(), ResourceFactory()])
            for _ in range(3)
        ]
        not_org_dataset = DatasetFactory(resources=[ResourceFactory()])
        hidden_dataset = DatasetFactory()

        response = self.get(
            url_for('organizations.datasets_resources_csv', org=org))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO(response.data.decode('utf-8'))
        reader = csv.get_reader(csvfile)
        header = next(reader)

        self.assertEqual(header[0], 'dataset.id')
        self.assertIn('dataset.title', header)
        self.assertIn('dataset.url', header)
        self.assertIn('title', header)
        self.assertIn('filetype', header)
        self.assertIn('url', header)
        self.assertIn('created_at', header)
        self.assertIn('modified', header)
        self.assertIn('downloads', header)

        resource_id_index = header.index('id')

        rows = list(reader)
        ids = [(row[0], row[resource_id_index]) for row in rows]

        self.assertEqual(len(rows), sum(len(d.resources) for d in datasets))
        for dataset in datasets:
            for resource in dataset.resources:
                self.assertIn((str(dataset.id), str(resource.id)), ids)

        dataset_ids = set(row[0] for row in rows)
        self.assertNotIn(str(hidden_dataset.id), dataset_ids)
        self.assertNotIn(str(not_org_dataset.id), dataset_ids)


class OrganizationBadgeAPITest:
    settings = GouvFrSettings
    modules = []

    @pytest.fixture(autouse=True)
    def setUp(self, api, clean_db):
        # Register at least two badges
        Organization.__badges__['test-1'] = 'Test 1'
        Organization.__badges__['test-2'] = 'Test 2'

        self.factory = badge_factory(Organization)
        self.user = api.login(AdminFactory())
        self.organization = OrganizationFactory()

    def test_create_badge_certified_mail(self, api):
        member = Member(user=self.user, role='admin')
        org = OrganizationFactory(members=[member])

        data = self.factory.as_dict()
        data['kind'] = CERTIFIED

        with capture_mails() as mails:
            api.post(url_for('api.organization_badges', org=org), data)

        # Should have sent one mail to each member of organization
        members_emails = [m.user.email for m in org.members]
        assert len(mails) == len(members_emails)
        assert [m.recipients[0] for m in mails] == members_emails

    def test_create_badge_public_service_mail(self, api):
        member = Member(user=self.user, role='admin')
        org = OrganizationFactory(members=[member])

        data = self.factory.as_dict()
        data['kind'] = PUBLIC_SERVICE

        with capture_mails() as mails:
            api.post(url_for('api.organization_badges', org=org), data)
            # do it a second time, no email expected for this one
            api.post(url_for('api.organization_badges', org=self.organization), data)

        # Should have sent one mail to each member of organization
        members_emails = [m.user.email for m in org.members]
        assert len(mails) == len(members_emails)
        assert [m.recipients[0] for m in mails] == members_emails


class DiscussionCsvTest(GouvfrFrontTestCase):
    settings = GouvFrSettings
    modules = []

    def test_discussions_csv_content_empty(self):
        organization = OrganizationFactory()
        response = self.get(
            url_for('organizations.discussions_csv', org=organization))
        self.assert200(response)

        self.assertEqual(
            response.data.decode('utf8'),
            ('"id";"user";"subject";"title";"size";"messages";"created";'
             '"closed";"closed_by"\r\n')
        )

    def test_discussions_csv_content_filled(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        user = UserFactory(first_name='John', last_name='Snow')
        discussion = DiscussionFactory(subject=dataset, user=user)
        response = self.get(
            url_for('organizations.discussions_csv', org=organization))
        self.assert200(response)

        headers, data = response.data.decode('utf-8').strip().split('\r\n')
        expected = '"{discussion.id}";"{discussion.user}"'
        assert_starts_with(data, expected.format(discussion=discussion))
