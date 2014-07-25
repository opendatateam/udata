# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import Organization, Member, MembershipRequest

from . import APITestCase
from ..factories import OrganizationFactory, UserFactory


class OrganizationAPITest(APITestCase):
    def test_organization_api_list(self):
        '''It should fetch an organization list from the API'''
        with self.autoindex():
            organizations = [OrganizationFactory() for i in range(3)]

        response = self.get(url_for('api.organizations'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(organizations))

    # def test_organization_api_get_not_found(self):
    #     '''It should raise 404 on API fetch if not found'''
    #     response = self.w.get(url_for('api.organization', slug='not-found'))
    #     self.assertEqual(response.status_code, 404)

    def test_organization_api_get(self):
        '''It should fetch an organization from the API'''
        organization = OrganizationFactory()
        response = self.get(url_for('api.organization', slug=organization.slug))
        self.assert200(response)

    def test_organization_api_create(self):
        '''It should create an organization from the API'''
        data = OrganizationFactory.attributes()
        self.login()
        response = self.post(url_for('api.organizations'), data)
        self.assertStatus(response, 201)
        self.assertEqual(Organization.objects.count(), 1)

    def test_dataset_api_update(self):
        '''It should update an organization from the API'''
        org = OrganizationFactory()
        data = org.to_dict()
        data['description'] = 'new description'
        self.login()
        response = self.put(url_for('api.organization', slug=org.slug), data)
        self.assert200(response)
        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(Organization.objects.first().description, 'new description')

    def test_organization_api_delete(self):
        '''It should delete an organization from the API'''
        organization = OrganizationFactory()
        with self.api_user():
            response = self.delete(url_for('api.organization', slug=organization.slug))
        self.assertStatus(response, 204)
        self.assertEqual(Organization.objects.count(), 1)
        self.assertIsNotNone(Organization.objects[0].deleted)

    # def test_organization_api_delete_not_found(self):
    #     '''It should raise a 404 on delete from the API if not found'''
    #     OrganizationFactory()
    #     response = self.w.delete(url_for('api.organization', slug='not-found'))
    #     self.assertEqual(response.status_code, 404)
    #     self.assertEqual(Organization.objects.count(), 1)


class MembershipAPITest(APITestCase):
    def test_request_membership(self):
        organization = OrganizationFactory()
        user = self.login()
        data = {'comment': 'a comment'}

        api_url = url_for('api.request_membership', org=organization)
        response = self.post(api_url, data)
        self.assertStatus(response, 201)

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
        organization = OrganizationFactory(members=[member], requests=[membership_request])

        api_url = url_for('api.accept_membership', org=organization, id=membership_request.id)
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

        api_url = url_for('api.accept_membership', org=organization, id=MembershipRequest().id)
        response = self.post(api_url)
        self.assert404(response)

        self.assertEqual(response.json, {'status': 404, 'message': 'Unknown membership request id'})

    def test_refuse_membership(self):
        user = self.login()
        applicant = UserFactory()
        membership_request = MembershipRequest(user=applicant, comment='test')
        member = Member(user=user, role='admin')
        organization = OrganizationFactory(members=[member], requests=[membership_request])
        data = {'comment': 'no'}

        api_url = url_for('api.refuse_membership', org=organization, id=membership_request.id)
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

        api_url = url_for('api.refuse_membership', org=organization, id=MembershipRequest().id)
        response = self.post(api_url)
        self.assert404(response)

        self.assertEqual(response.json, {'status': 404, 'message': 'Unknown membership request id'})
