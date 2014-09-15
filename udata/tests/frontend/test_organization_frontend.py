# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import StringIO

from flask import url_for

from udata.frontend import csv
from udata.models import Organization, Member, FollowOrg

from . import FrontTestCase
from ..factories import OrganizationFactory, UserFactory, DatasetFactory, ResourceFactory


class OrganizationBlueprintTest(FrontTestCase):
    def test_render_list(self):
        '''It should render the organization list page'''
        with self.autoindex():
            organizations = [OrganizationFactory() for i in range(3)]

        response = self.get(url_for('organizations.list'))

        self.assert200(response)
        rendered_organizations = self.get_context_variable('organizations')
        self.assertEqual(len(rendered_organizations), len(organizations))

    def test_render_list_empty(self):
        '''It should render the organization list page event if empty'''
        response = self.get(url_for('organizations.list'))
        self.assert200(response)

    def test_render_create(self):
        '''It should render the organization create form'''
        response = self.get(url_for('organizations.new'))
        self.assert200(response)

    def test_create(self):
        '''It should create a organization and redirect to organization page'''
        data = OrganizationFactory.attributes()
        self.login()
        response = self.post(url_for('organizations.new'), data)

        organization = Organization.objects.first()
        self.assertRedirects(response, organization.display_url)

    def test_render_display(self):
        '''It should render the organization page'''
        organization = OrganizationFactory()
        response = self.get(url_for('organizations.show', org=organization))
        self.assert200(response)

    def test_render_display_with_followers(self):
        '''It should render the organization page with followers'''
        org = OrganizationFactory()
        followers = [FollowOrg.objects.create(follower=UserFactory(), following=org) for _ in range(3)]

        response = self.get(url_for('organizations.show', org=org))
        self.assert200(response)

        rendered_followers = self.get_context_variable('followers')
        self.assertEqual(len(rendered_followers), len(followers))

    def test_render_edit(self):
        '''It should render the organization edit form'''
        user = self.login()
        organization = OrganizationFactory(members=[Member(user=user, role='admin')])

        response = self.get(url_for('organizations.edit', org=organization))
        self.assert200(response)

    def test_edit(self):
        '''It should handle edit form submit and redirect on organization page'''
        user = self.login()

        organization = OrganizationFactory(members=[Member(user=user, role='admin')])
        data = organization.to_dict()
        del data['members']
        data['description'] = 'new description'
        response = self.post(url_for('organizations.edit', org=organization), data)

        organization.reload()
        self.assertRedirects(response, organization.display_url)
        self.assertEqual(organization.description, 'new description')

    def test_delete(self):
        '''It should handle deletion from form submit and redirect on organization page'''
        user = self.login()

        organization = OrganizationFactory(members=[Member(user=user, role='admin')])
        response = self.post(url_for('organizations.delete', org=organization))

        organization.reload()
        self.assertRedirects(response, organization.display_url)
        self.assertIsNotNone(organization.deleted)

    def test_render_edit_extras(self):
        '''It should render the organization extras edit form'''
        user = self.login()
        organization = OrganizationFactory(members=[Member(user=user, role='admin')])
        response = self.get(url_for('organizations.edit_extras', org=organization))
        self.assert200(response)

    def test_add_extras(self):
        user = self.login()
        organization = OrganizationFactory(members=[Member(user=user, role='admin')])
        data = {'key': 'a_key', 'value': 'a_value'}

        response = self.post(url_for('organizations.edit_extras', org=organization), data)

        self.assert200(response)
        organization.reload()
        self.assertIn('a_key', organization.extras)
        self.assertEqual(organization.extras['a_key'], 'a_value')

    def test_update_extras(self):
        user = self.login()
        organization = OrganizationFactory(members=[Member(user=user, role='admin')], extras={'a_key': 'a_value'})
        data = {'key': 'a_key', 'value': 'new_value'}

        response = self.post(url_for('organizations.edit_extras', org=organization), data)

        self.assert200(response)
        organization.reload()
        self.assertIn('a_key', organization.extras)
        self.assertEqual(organization.extras['a_key'], 'new_value')

    def test_rename_extras(self):
        user = self.login()
        organization = OrganizationFactory(members=[Member(user=user, role='admin')], extras={'a_key': 'a_value'})
        data = {'key': 'new_key', 'value': 'a_value', 'old_key': 'a_key'}

        response = self.post(url_for('organizations.edit_extras', org=organization), data)

        self.assert200(response)
        organization.reload()
        self.assertIn('new_key', organization.extras)
        self.assertEqual(organization.extras['new_key'], 'a_value')
        self.assertNotIn('a_key', organization.extras)

    def test_delete_extras(self):
        user = self.login()
        organization = OrganizationFactory(members=[Member(user=user, role='admin')], extras={'a_key': 'a_value'})

        response = self.delete(url_for('organizations.delete_extra', org=organization, extra='a_key'))

        self.assert200(response)
        organization.reload()
        self.assertNotIn('a_key', organization.extras)

    def test_render_edit_members(self):
        '''It should render the organization member edit page'''
        user = self.login()
        organization = OrganizationFactory(members=[Member(user=user, role='admin')])
        response = self.get(url_for('organizations.edit_members', org=organization))
        self.assert200(response)

    def test_add_member(self):
        '''It should add a member to the organization'''
        user = self.login()
        new_user = UserFactory()
        organization = OrganizationFactory(members=[Member(user=user, role='admin')])
        data = {'pk': str(new_user.id)}
        response = self.post(url_for('organizations.edit_members', org=organization), data)
        self.assert200(response)

        organization.reload()
        self.assertEqual(len(organization.members), 2)

        new_member = organization.members[1]
        self.assertEqual(new_member.user, new_user)
        self.assertEqual(new_member.role, 'editor')

    def test_change_member_role(self):
        '''It should edit a member role into the organization'''
        user = self.login()
        user_modified = UserFactory()
        organization = OrganizationFactory(members=[
            Member(user=user, role='admin'),
            Member(user=user_modified, role='editor'),
        ])
        data = {'pk': str(user_modified.id), 'value': 'admin'}
        response = self.post(url_for('organizations.edit_members', org=organization), data)
        self.assert200(response)

        organization.reload()
        self.assertEqual(len(organization.members), 2)

        member = organization.members[1]
        self.assertEqual(member.user, user_modified)
        self.assertEqual(member.role, 'admin')

    def test_remove_member(self):
        '''It should remove a member from the organization'''
        user = self.login()
        deleted = UserFactory()
        organization = OrganizationFactory(members=[
            Member(user=user, role='admin'),
            Member(user=deleted, role='editor'),
        ])
        data = {'user_id': str(deleted.id)}
        response = self.delete(url_for('organizations.edit_members', org=organization), data, content_type='multipart/form-data')
        self.assertStatus(response, 204)

        organization.reload()
        self.assertEqual(len(organization.members), 1)

        self.assertEqual(organization.members[0].user, user)

    def test_render_edit_teams(self):
        '''It should render the organization team edit form'''
        user = self.login()
        organization = OrganizationFactory(members=[Member(user=user, role='admin')])

        response = self.get(url_for('organizations.edit_teams', org=organization))
        self.assert200(response)

    def test_not_found(self):
        '''It should render the organization page'''
        response = self.get(url_for('organizations.show', org='not-found'))
        self.assert404(response)

    def test_render_issues(self):
        '''It should render the organization issues page'''
        user = self.login()
        organization = OrganizationFactory(members=[Member(user=user, role='admin')])
        response = self.get(url_for('organizations.issues', org=organization))
        self.assert200(response)

    def test_datasets_csv(self):
        with self.autoindex():
            org = OrganizationFactory()
            datasets = [DatasetFactory(organization=org, resources=[ResourceFactory()]) for _ in range(3)]
            not_org_dataset = DatasetFactory(resources=[ResourceFactory()])
            hidden_dataset = DatasetFactory()

        response = self.get(url_for('organizations.datasets_csv', org=org))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO.StringIO(response.data)
        reader = reader = csv.get_reader(csvfile)
        header = reader.next()

        self.assertEqual(header[0], 'id')
        self.assertIn('title', header)
        self.assertIn('description', header)
        self.assertIn('created_at', header)
        self.assertIn('last_modified', header)
        self.assertIn('tags', header)
        self.assertIn('metric.reuses', header)

        rows = list(reader)
        ids = [row[0] for row in rows]

        self.assertEqual(len(rows), len(datasets))
        for dataset in datasets:
            self.assertIn(str(dataset.id), ids)
        self.assertNotIn(str(hidden_dataset.id), ids)
        self.assertNotIn(str(not_org_dataset.id), ids)

    def test_supplied_datasets_csv(self):
        with self.autoindex():
            org = OrganizationFactory()
            datasets = [DatasetFactory(supplier=org, resources=[ResourceFactory()]) for _ in range(3)]
            not_org_dataset = DatasetFactory(resources=[ResourceFactory()])
            hidden_dataset = DatasetFactory()

        response = self.get(url_for('organizations.supplied_datasets_csv', org=org))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO.StringIO(response.data)
        reader = csv.get_reader(csvfile)
        header = reader.next()

        self.assertEqual(header[0], 'id')
        self.assertIn('title', header)
        self.assertIn('description', header)
        self.assertIn('created_at', header)
        self.assertIn('last_modified', header)
        self.assertIn('tags', header)
        self.assertIn('metric.reuses', header)

        rows = list(reader)
        ids = [row[0] for row in rows]

        self.assertEqual(len(rows), len(datasets))
        for dataset in datasets:
            self.assertIn(str(dataset.id), ids)
        self.assertNotIn(str(hidden_dataset.id), ids)
        self.assertNotIn(str(not_org_dataset.id), ids)

    def test_render_activity_empty(self):
        org = OrganizationFactory()
        response = self.get(url_for('organizations.activity', org=org))
        self.assert200(response)
