# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import FollowOrg, FollowDataset

from udata.tests.frontend import FrontTestCase
from udata.tests.factories import OrganizationFactory, UserFactory, DatasetFactory


class FollowersBlueprintTest(FrontTestCase):
    def test_org_followers(self):
        '''It should render the organization followers list page'''
        org = OrganizationFactory()
        followers = [FollowOrg.objects.create(follower=UserFactory(), following=org) for _ in range(3)]

        response = self.get(url_for('followers.organization', org=org))

        self.assert200(response)
        rendered_followers = self.get_context_variable('followers')
        self.assertEqual(len(rendered_followers), len(followers))

    def test_dataset_followers(self):
        '''It should render the dataset followers list page'''
        dataset = DatasetFactory()
        followers = [FollowDataset.objects.create(follower=UserFactory(), following=dataset) for _ in range(3)]

        response = self.get(url_for('followers.dataset', dataset=dataset))

        self.assert200(response)
        rendered_followers = self.get_context_variable('followers')
        self.assertEqual(len(rendered_followers), len(followers))

