from flask import url_for

from udata.models import Follow
from udata.core.user.factories import UserFactory, AdminFactory
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.organization.factories import OrganizationFactory
from udata_front.tests import GouvFrSettings
from udata_front.tests.frontend import GouvfrFrontTestCase


class UserBlueprintTest(GouvfrFrontTestCase):
    settings = GouvFrSettings
    modules = ['admin']

    def test_render_profile(self):
        '''It should render the user profile'''
        user = UserFactory(about='* Title 1\n* Title 2',
                           website='http://www.datagouv.fr/user',
                           avatar_url='http://www.datagouv.fr/avatar')
        response = self.get(url_for('users.show', user=user))
        self.assert200(response)
        json_ld = self.get_json_ld(response)
        self.assertEqual(json_ld['@context'], 'http://schema.org')
        self.assertEqual(json_ld['@type'], 'Person')
        self.assertEqual(json_ld['name'], user.fullname)
        self.assertEqual(json_ld['description'], 'Title 1 Title 2')
        self.assertEqual(json_ld['url'], 'http://www.datagouv.fr/user')
        self.assertEqual(json_ld['image'], 'http://www.datagouv.fr/avatar')

    def test_cannot_render_profile_of_an_inactive_user(self):
        '''It should raise a 410 when the user is inactive'''
        user = UserFactory(active=False)
        response = self.get(url_for('users.show', user=user))
        self.assert410(response)

    def test_render_profile_of_an_inactive_user_when_admin(self):
        '''It should render the user profile'''
        self.login(AdminFactory())
        user = UserFactory(active=True)
        response = self.get(url_for('users.show', user=user))
        self.assert200(response)

    def test_render_profile_datasets(self):
        '''It should render the user profile datasets page'''
        user = UserFactory()
        datasets = [DatasetFactory(owner=user, resources=[ResourceFactory()])
                    for _ in range(3)]
        for _ in range(2):
            DatasetFactory(resources=[ResourceFactory()])
        response = self.get(url_for('users.datasets', user=user))
        self.assert200(response)
        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets), len(datasets))

    def test_render_profile_reuses(self):
        '''It should render the user profile reuses page'''
        user = UserFactory()
        reuses = [ReuseFactory(owner=user, datasets=[DatasetFactory()])
                  for _ in range(3)]
        for _ in range(2):
            ReuseFactory(datasets=[DatasetFactory()])
        response = self.get(url_for('users.reuses', user=user))
        self.assert200(response)
        rendered_reuses = self.get_context_variable('reuses')
        self.assertEqual(len(rendered_reuses), len(reuses))

    def test_render_profile_following(self):
        '''It should render the user profile following page'''
        user = UserFactory()
        for _ in range(2):
            reuse = ReuseFactory()
            Follow.objects.create(follower=user, following=reuse)
            dataset = DatasetFactory()
            Follow.objects.create(follower=user, following=dataset)
            org = OrganizationFactory()
            Follow.objects.create(follower=user, following=org)
            other_user = UserFactory()
            Follow.objects.create(follower=user, following=other_user)
        response = self.get(url_for('users.following', user=user))
        self.assert200(response)
        for name in 'datasets', 'users', 'reuses', 'organizations':
            rendered = self.get_context_variable('followed_{0}'.format(name))
            self.assertEqual(len(rendered), 2)

    def test_render_profile_followers(self):
        '''It should render the user profile followers page'''
        user = UserFactory()
        followers = [
            Follow.objects.create(follower=UserFactory(), following=user)
            for _ in range(3)
        ]
        response = self.get(url_for('users.followers', user=user))

        self.assert200(response)

        rendered_followers = self.get_context_variable('followers')
        self.assertEqual(len(rendered_followers), len(followers))

    def test_render_profile_following_empty(self):
        '''It should render an empty user profile following page'''
        user = UserFactory()
        response = self.get(url_for('users.following', user=user))
        self.assert200(response)

    def test_not_found(self):
        '''It should raise 404 if user is not found'''
        response = self.get(url_for('users.show', user='not-found'))
        self.assert404(response)
