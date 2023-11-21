from flask import url_for

from udata.core import storages
from udata.core.user.factories import AdminFactory, UserFactory
from udata.models import Follow
from udata.utils import faker
from udata.tests.helpers import create_test_image

from . import APITestCase


class UserAPITest(APITestCase):
    modules = []

    def test_follow_user(self):
        '''It should follow an user on POST'''
        user = self.login()
        to_follow = UserFactory()

        response = self.post(url_for('api.user_followers', id=to_follow.id))
        self.assert201(response)

        to_follow.count_followers()
        self.assertEqual(to_follow.get_metrics()['followers'], 1)

        nb_followers = Follow.objects.followers(to_follow).count()

        self.assertEqual(response.json['followers'], nb_followers)
        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(nb_followers, 1)
        self.assertIsInstance(Follow.objects.followers(to_follow).first(),
                              Follow)
        self.assertEqual(Follow.objects.following(user).count(), 1)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_follow_myself(self):
        '''It should not allow to follow myself'''
        user = self.login()

        response = self.post(url_for('api.user_followers', id=user.id))
        self.assertStatus(response, 403)

        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_unfollow(self):
        '''It should unfollow the user on DELETE'''
        user = self.login()
        to_follow = UserFactory()
        Follow.objects.create(follower=user, following=to_follow)

        response = self.delete(url_for('api.user_followers', id=to_follow.id))
        self.assert200(response)

        nb_followers = Follow.objects.followers(to_follow).count()

        self.assertEqual(response.json['followers'], nb_followers)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(nb_followers, 0)
        self.assertEqual(Follow.objects.following(user).count(), 0)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_suggest_users_api_first_name(self):
        '''It should suggest users based on first name'''
        for i in range(4):
            UserFactory(
                first_name='first-name-test-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.suggest_users'),
                            qs={'q': 'first-name-test', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('first_name', suggestion)
            self.assertIn('last_name', suggestion)
            self.assertIn('avatar_url', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('first-name-test', suggestion['first_name'])

    def test_suggest_users_api_last_name(self):
        '''It should suggest users based on last name'''
        for i in range(4):
            UserFactory(
                last_name='last-name-test-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.suggest_users'),
                            qs={'q': 'last-name-test', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('first_name', suggestion)
            self.assertIn('last_name', suggestion)
            self.assertIn('avatar_url', suggestion)
            self.assertIn('last-name-test', suggestion['last_name'])

    def test_suggest_users_api_unicode(self):
        '''It should suggest users with special characters'''
        for i in range(4):
            UserFactory(
                last_name='last-name-testé-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.suggest_users'),
                            qs={'q': 'last-name-testé', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('first_name', suggestion)
            self.assertIn('last_name', suggestion)
            self.assertIn('avatar_url', suggestion)
            self.assertIn('last-name-testé', suggestion['last_name'])

    def test_suggest_users_api_no_match(self):
        '''It should not provide user suggestion if no match'''
        UserFactory.create_batch(3)

        response = self.get(url_for('api.suggest_users'),
                            qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_users_api_empty(self):
        '''It should not provide user suggestion if no data'''
        response = self.get(url_for('api.suggest_users'),
                            qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_users_api_no_dedup(self):
        '''It should suggest users without deduplicating homonyms'''
        UserFactory.create_batch(2, first_name='test', last_name='homonym')

        response = self.get(url_for('api.suggest_users'),
                            qs={'q': 'homonym', 'size': '5'})
        self.assert200(response)

        self.assertEqual(len(response.json), 2)

        for suggestion in response.json:
            self.assertEqual(suggestion['first_name'], 'test')
            self.assertEqual(suggestion['last_name'], 'homonym')

    def test_user_api_full_text_search_first_name(self):
        '''It should find users based on first name'''
        for i in range(4):
            UserFactory(
                first_name='test-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.users', q='test'))
        self.assert200(response)

        self.assertEqual(len(response.json['data']), 2)

    def test_user_api_full_text_search_last_name(self):
        '''It should find users based on last name'''
        for i in range(4):
            UserFactory(
                last_name='test-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.users', q='test'))
        self.assert200(response)

        self.assertEqual(len(response.json['data']), 2)

    def test_user_api_full_text_search_unicode(self):
        '''It should find user with special characters'''
        for i in range(4):
            UserFactory(
                first_name='test-{0}'.format(i) if i % 2 else faker.word())

        user = UserFactory(first_name='test', last_name='testé')

        response = self.get(url_for('api.users', q='test testé'))
        self.assert200(response)

        self.assertEqual(len(response.json['data']), 3)
        self.assertEqual(response.json['data'][0]['id'], str(user.id))

    def test_find_users_api_no_match(self):
        '''It should not find user if no match'''
        UserFactory.create_batch(3)

        response = self.get(url_for('api.users', q='xxxxxx'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 0)

    def test_users(self):
        '''It should provide a list of users'''
        user = UserFactory(
            about=faker.paragraph(),
            website=faker.url(),
            avatar_url=faker.url(),
            metrics={'datasets': 10, 'followers': 1, 'following': 0, 'reuses': 2})
        response = self.get(url_for('api.users'))
        self.assert200(response)
        [json] = response.json['data']
        self.assertEqual(json['id'], str(user.id))
        self.assertEqual(json['slug'], user.slug)
        self.assertEqual(json['first_name'], user.first_name)
        self.assertEqual(json['last_name'], user.last_name)
        self.assertEqual(json['website'], user.website)
        self.assertEqual(json['about'], user.about)
        self.assertEqual(json['metrics'], user.metrics)

    def test_get_user(self):
        '''It should get a user'''
        user = UserFactory()
        response = self.get(url_for('api.user', user=user))
        self.assert200(response)

    def test_get_inactive_user(self):
        '''It should raise a 410'''
        user = UserFactory(active=False)
        response = self.get(url_for('api.user', user=user))
        self.assert410(response)

    def test_get_inactive_user_with_a_non_admin(self):
        '''It should raise a 410'''
        user = UserFactory(active=False)
        self.login()
        response = self.get(url_for('api.user', user=user))
        self.assert410(response)

    def test_change_avatar_user_with_a_non_admin(self):
        '''It should raise a 403'''
        user = UserFactory(active=True)
        self.login()
        response = self.post(url_for('api.user_avatar', user=user))
        self.assert403(response)

    def test_get_inactive_user_with_an_admin(self):
        '''It should get a user'''
        user = UserFactory(active=False)
        self.login(AdminFactory())
        response = self.get(url_for('api.user', user=user))
        self.assert200(response)

    def test_user_api_create_as_admin(self):
        '''It should create a user'''
        self.login(AdminFactory())
        data = {
            "first_name": faker.first_name(),
            "last_name": faker.last_name(),
            "email": faker.email()
        }
        response = self.post(url_for('api.users'), data=data)
        self.assert201(response)

    def test_user_api_create_as_no_admin(self):
        '''It should not create a user'''
        self.login(UserFactory())
        data = {
            "first_name": faker.first_name(),
            "last_name": faker.last_name(),
            "email": faker.email()
        }
        response = self.post(url_for('api.users'), data=data)
        self.assert403(response)

    def test_user_api_update(self):
        '''It should update a user'''
        self.login(AdminFactory())
        user = UserFactory()
        data = user.to_dict()
        data['active'] = False
        response = self.put(url_for('api.user', user=user), data)
        self.assert200(response)
        self.assertFalse(response.json['active'])

    def test_user_api_update_with_website(self):
        '''It should raise a 400'''
        self.login(AdminFactory())
        user = UserFactory()
        data = user.to_dict()
        data['website'] = 'foo'
        response = self.put(url_for('api.user', user=user), data)
        self.assert400(response)
        data['website'] = faker.url()
        response = self.put(url_for('api.user', user=user), data)
        self.assert200(response)

    def test_user_api_update_with_a_non_admin_connected_user(self):
        '''It should raise a 403'''
        user = UserFactory()
        self.login(user)
        data = user.to_dict()
        response = self.put(url_for('api.user', user=user), data)
        self.assert403(response)

    def test_user_api_update_with_an_existing_role(self):
        '''It should update a user'''
        self.login(AdminFactory())
        user = UserFactory()
        data = user.to_dict()
        data['roles'] = ['admin']
        response = self.put(url_for('api.user', user=user), data)
        self.assert200(response)
        self.assertEqual(response.json['roles'], ['admin'])

    def test_user_api_update_with_a_non_existing_role(self):
        '''It should raise a 400'''
        self.login(AdminFactory())
        user = UserFactory()
        data = user.to_dict()
        data['roles'] = ['non_existing_role']
        response = self.put(url_for('api.user', user=user), data)
        self.assert400(response)

    def test_user_roles(self):
        '''It should list the roles'''
        self.login(AdminFactory())
        response = self.get(url_for('api.user_roles'))
        self.assert200(response)
        self.assertEqual(response.json, [{'name': 'admin'}])

    def test_delete_user(self):
        user = AdminFactory()
        self.login(user)
        other_user = UserFactory()
        file = create_test_image()

        response = self.post(
            url_for('api.user_avatar', user=other_user),
            {'file': (file, 'test.png')},
            json=False,
        )
        response = self.delete(url_for('api.user', user=other_user))
        self.assertEqual(list(storages.avatars.list_files()), [])
        self.assert204(response)
        other_user.reload()
        response = self.delete(url_for('api.user', user=other_user))
        self.assert410(response)
        response = self.delete(url_for('api.user', user=user))
        self.assert403(response)

    def test_contact_points(self):
        user = AdminFactory()
        self.login(user)
        user = UserFactory()
        data = {
            'email': 'mooneywayne@cobb-cochran.com',
            'name': 'Martin Schultz',
            'owner': str(user.id)
        }

        response = self.post(url_for('api.contact_points'), data)
        self.assert201(response)

        response = self.get(url_for('api.user_contact_points', user=user))
        self.assert200(response)

        assert response.json['data'][0]['name'] == data['name']
        assert response.json['data'][0]['email'] == data['email']
