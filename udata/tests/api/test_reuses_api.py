import pytest

from datetime import datetime

from flask import url_for

from udata.core.badges.factories import badge_factory
from udata.core.dataset.factories import DatasetFactory
from udata.core.user.factories import AdminFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.models import Reuse, Follow, Member, REUSE_TOPICS, REUSE_TYPES
from udata.utils import faker

from udata.tests.helpers import (
    assert200, assert201, assert204, assert400, assert404, assert410
)


pytestmark = [
    pytest.mark.usefixtures('clean_db'),
]


class ReuseAPITest:
    modules = []

    def test_reuse_api_list(self, api):
        '''It should fetch a reuse list from the API'''
        reuses = ReuseFactory.create_batch(3, visible=True)

        response = api.get(url_for('api.reuses'))
        assert200(response)
        assert len(response.json['data']) == len(reuses)

    def test_reuse_api_list_with_filters(self, api):
        '''Should filters reuses results based on query filters'''
        owner = UserFactory()
        org = OrganizationFactory()

        [ReuseFactory() for i in range(2)]

        tag_reuse = ReuseFactory(tags=['my-tag', 'other'])
        owner_reuse = ReuseFactory(owner=owner)
        org_reuse = ReuseFactory(organization=org)

        # filter on tag
        response = api.get(url_for('api.reuses', tag='my-tag'))
        assert200(response)
        assert len(response.json['data']) == 1
        assert response.json['data'][0]['id'] == str(tag_reuse.id)

        # filter on owner
        response = api.get(url_for('api.reuses', owner=owner.id))
        assert200(response)
        assert len(response.json['data']) == 1
        assert response.json['data'][0]['id'] == str(owner_reuse.id)

        # filter on organization
        response = api.get(url_for('api.reuses', organization=org.id))
        assert200(response)
        assert len(response.json['data']) == 1
        assert response.json['data'][0]['id'] == str(org_reuse.id)

    def test_reuse_api_get(self, api):
        '''It should fetch a reuse from the API'''
        reuse = ReuseFactory()
        response = api.get(url_for('api.reuse', reuse=reuse))
        assert200(response)

    def test_reuse_api_get_deleted(self, api):
        '''It should not fetch a deleted reuse from the API and raise 410'''
        reuse = ReuseFactory(deleted=datetime.now())
        response = api.get(url_for('api.reuse', reuse=reuse))
        assert410(response)

    def test_reuse_api_get_deleted_but_authorized(self, api):
        '''It should fetch a deleted reuse from the API if authorized'''
        user = api.login()
        reuse = ReuseFactory(deleted=datetime.now(), owner=user)
        response = api.get(url_for('api.reuse', reuse=reuse))
        assert200(response)

    def test_reuse_api_create(self, api):
        '''It should create a reuse from the API'''
        data = ReuseFactory.as_dict()
        user = api.login()
        response = api.post(url_for('api.reuses'), data)
        assert201(response)
        assert Reuse.objects.count() == 1

        reuse = Reuse.objects.first()
        assert reuse.owner == user
        assert reuse.organization is None

    def test_reuse_api_create_as_org(self, api):
        '''It should create a reuse as organization from the API'''
        user = api.login()
        data = ReuseFactory.as_dict()
        member = Member(user=user, role='editor')
        org = OrganizationFactory(members=[member])
        data['organization'] = str(org.id)
        response = api.post(url_for('api.reuses'), data)
        assert201(response)
        assert Reuse.objects.count() == 1

        reuse = Reuse.objects.first()
        assert reuse.owner is None
        assert reuse.organization == org

    def test_reuse_api_create_as_permissions(self, api):
        """It should create a reuse as organization from the API

        only if user is member.
        """
        api.login()
        data = ReuseFactory.as_dict()
        org = OrganizationFactory()
        data['organization'] = str(org.id)
        response = api.post(url_for('api.reuses'), data)
        assert400(response)
        assert Reuse.objects.count() == 0

    def test_reuse_api_update(self, api):
        '''It should update a reuse from the API'''
        user = api.login()
        reuse = ReuseFactory(owner=user)
        data = reuse.to_dict()
        data['description'] = 'new description'
        response = api.put(url_for('api.reuse', reuse=reuse), data)
        assert200(response)
        assert Reuse.objects.count() == 1
        assert Reuse.objects.first().description == 'new description'

    def test_reuse_api_update_deleted(self, api):
        '''It should not update a deleted reuse from the API and raise 410'''
        api.login()
        reuse = ReuseFactory(deleted=datetime.now())
        response = api.put(url_for('api.reuse', reuse=reuse), {})
        assert410(response)

    def test_reuse_api_delete(self, api):
        '''It should delete a reuse from the API'''
        user = api.login()
        reuse = ReuseFactory(owner=user)
        response = api.delete(url_for('api.reuse', reuse=reuse))
        assert204(response)
        assert Reuse.objects.count() == 1
        assert Reuse.objects[0].deleted is not None

    def test_reuse_api_delete_deleted(self, api):
        '''It should not delete a deleted reuse from the API and raise 410'''
        api.login()
        reuse = ReuseFactory(deleted=datetime.now())
        response = api.delete(url_for('api.reuse', reuse=reuse))
        assert410(response)

    def test_reuse_api_add_dataset(self, api):
        '''It should add a dataset to a reuse from the API'''
        user = api.login()
        reuse = ReuseFactory(owner=user)

        dataset = DatasetFactory()
        data = {'id': dataset.id, 'class': 'Dataset'}
        url = url_for('api.reuse_add_dataset', reuse=reuse)
        response = api.post(url, data)
        assert201(response)
        reuse.reload()
        assert len(reuse.datasets) == 1
        assert reuse.datasets[-1] == dataset

        dataset = DatasetFactory()
        data = {'id': dataset.id, 'class': 'Dataset'}
        url = url_for('api.reuse_add_dataset', reuse=reuse)
        response = api.post(url, data)
        assert201(response)
        reuse.reload()
        assert len(reuse.datasets) == 2
        assert reuse.datasets[-1] == dataset

    def test_reuse_api_add_dataset_twice(self, api):
        '''It should not add twice a dataset to a reuse from the API'''
        user = api.login()
        dataset = DatasetFactory()
        reuse = ReuseFactory(owner=user, datasets=[dataset])

        data = {'id': dataset.id, 'class': 'Dataset'}
        url = url_for('api.reuse_add_dataset', reuse=reuse)
        response = api.post(url, data)
        assert200(response)
        reuse.reload()
        assert len(reuse.datasets) == 1
        assert reuse.datasets[-1] == dataset

    def test_reuse_api_add_dataset_not_found(self, api):
        '''It should return 404 when adding an unknown dataset to a reuse'''
        user = api.login()
        reuse = ReuseFactory(owner=user)

        data = {'id': 'not-found', 'class': 'Dataset'}
        url = url_for('api.reuse_add_dataset', reuse=reuse)
        response = api.post(url, data)

        assert404(response)
        reuse.reload()
        assert len(reuse.datasets) == 0

    def test_reuse_api_feature(self, api):
        '''It should mark the reuse featured on POST'''
        reuse = ReuseFactory(featured=False)

        with api.user(AdminFactory()):
            response = api.post(url_for('api.reuse_featured', reuse=reuse))
        assert200(response)

        reuse.reload()
        assert reuse.featured

    def test_reuse_api_feature_already(self, api):
        '''It shouldn't do anything to feature an already featured reuse'''
        reuse = ReuseFactory(featured=True)

        with api.user(AdminFactory()):
            response = api.post(url_for('api.reuse_featured', reuse=reuse))
        assert200(response)

        reuse.reload()
        assert reuse.featured

    def test_reuse_api_unfeature(self, api):
        '''It should mark the reuse featured on POST'''
        reuse = ReuseFactory(featured=True)

        with api.user(AdminFactory()):
            response = api.delete(url_for('api.reuse_featured', reuse=reuse))
        assert200(response)

        reuse.reload()
        assert not reuse.featured

    def test_reuse_api_unfeature_already(self, api):
        '''It shouldn't do anything to unfeature a not featured reuse'''
        reuse = ReuseFactory(featured=False)

        with api.user(AdminFactory()):
            response = api.delete(url_for('api.reuse_featured', reuse=reuse))
        assert200(response)

        reuse.reload()
        assert not reuse.featured

    def test_follow_reuse(self, api):
        '''It should follow a reuse on POST'''
        user = api.login()
        to_follow = ReuseFactory()

        response = api.post(url_for('api.reuse_followers', id=to_follow.id))
        assert201(response)

        to_follow.count_followers()
        assert to_follow.get_metrics()['followers'] == 1

        assert Follow.objects.following(to_follow).count() == 0
        assert Follow.objects.followers(to_follow).count() == 1
        follow = Follow.objects.followers(to_follow).first()
        assert isinstance(follow.following, Reuse)
        assert Follow.objects.following(user).count() == 1
        assert Follow.objects.followers(user).count() == 0

    def test_unfollow_reuse(self, api):
        '''It should unfollow the reuse on DELETE'''
        user = api.login()
        to_follow = ReuseFactory()
        Follow.objects.create(follower=user, following=to_follow)

        response = api.delete(url_for('api.reuse_followers', id=to_follow.id))
        assert200(response)

        nb_followers = Follow.objects.followers(to_follow).count()

        assert response.json['followers'] == nb_followers

        assert Follow.objects.following(to_follow).count() == 0
        assert nb_followers == 0
        assert Follow.objects.following(user).count() == 0
        assert Follow.objects.followers(user).count() == 0

    def test_suggest_reuses_api(self, api):
        '''It should suggest reuses'''
        for i in range(3):
            ReuseFactory(
                title='test-{0}'.format(i) if i % 2 else faker.word(),
                visible=True,
                metrics={"followers": i})
        max_follower_reuse = ReuseFactory(
            title='test-4',
            visible=True,
            metrics={"followers": 10}
        )

        response = api.get(url_for('api.suggest_reuses'),
                           qs={'q': 'tes', 'size': '5'})
        assert200(response)

        assert len(response.json) <= 5
        assert len(response.json) > 1

        for suggestion in response.json:
            assert 'id' in suggestion
            assert 'slug' in suggestion
            assert 'title' in suggestion
            assert 'image_url' in suggestion
            assert 'test' in suggestion['title']
        assert response.json[0]['id'] == str(max_follower_reuse.id)

    def test_suggest_reuses_api_unicode(self, api):
        '''It should suggest reuses with special characters'''
        for i in range(4):
            ReuseFactory(
                title='testé-{0}'.format(i) if i % 2 else faker.word(),
                visible=True)

        response = api.get(url_for('api.suggest_reuses'),
                           qs={'q': 'testé', 'size': '5'})
        assert200(response)

        assert len(response.json) <= 5
        assert len(response.json) > 1

        for suggestion in response.json:
            assert 'id' in suggestion
            assert 'slug' in suggestion
            assert 'title' in suggestion
            assert 'image_url' in suggestion
            assert 'test' in suggestion['title']

    def test_suggest_reuses_api_no_match(self, api):
        '''It should not provide reuse suggestion if no match'''
        ReuseFactory.create_batch(3, visible=True)

        response = api.get(url_for('api.suggest_reuses'),
                           qs={'q': 'xxxxxx', 'size': '5'})
        assert200(response)
        assert len(response.json) == 0

    def test_suggest_reuses_api_empty(self, api):
        '''It should not provide reuse suggestion if no data'''
        # self.init_search()
        response = api.get(url_for('api.suggest_reuses'),
                           qs={'q': 'xxxxxx', 'size': '5'})
        assert200(response)
        assert len(response.json) == 0


class ReuseBadgeAPITest:
    modules = []

    @pytest.fixture(autouse=True)
    def setup(self, api, clean_db):
        # Register at least two badges
        Reuse.__badges__['test-1'] = 'Test 1'
        Reuse.__badges__['test-2'] = 'Test 2'

        self.factory = badge_factory(Reuse)
        self.user = api.login(AdminFactory())
        self.reuse = ReuseFactory()

    def test_list(self, api):
        response = api.get(url_for('api.available_reuse_badges'))
        assert200(response)
        assert len(response.json) == len(Reuse.__badges__)
        for kind, label in Reuse.__badges__.items():
            assert kind in response.json
            assert response.json[kind] == label

    def test_create(self, api):
        data = self.factory.as_dict()
        response = api.post(url_for('api.reuse_badges', reuse=self.reuse), data)
        assert201(response)
        self.reuse.reload()
        assert len(self.reuse.badges) == 1

    def test_create_same(self, api):
        data = self.factory.as_dict()
        api.post(url_for('api.reuse_badges', reuse=self.reuse), data)
        response = api.post(url_for('api.reuse_badges', reuse=self.reuse), data)
        assert200(response)
        self.reuse.reload()
        assert len(self.reuse.badges) == 1

    def test_create_2nd(self, api):
        # Explicitely setting the kind to avoid collisions given the
        # small number of choices for kinds.
        kinds_keys = list(Reuse.__badges__)
        self.reuse.add_badge(kinds_keys[0])
        data = self.factory.as_dict()
        data['kind'] = kinds_keys[1]
        response = api.post(url_for('api.reuse_badges', reuse=self.reuse), data)
        assert201(response)
        self.reuse.reload()
        assert len(self.reuse.badges) == 2

    def test_delete(self, api):
        badge = self.factory()
        self.reuse.add_badge(badge.kind)
        response = api.delete(url_for('api.reuse_badge',
                                      reuse=self.reuse,
                                      badge_kind=str(badge.kind)))
        assert204(response)
        self.reuse.reload()
        assert len(self.reuse.badges) == 0

    def test_delete_404(self, api):
        response = api.delete(url_for('api.reuse_badge', reuse=self.reuse,
                                      badge_kind=str(self.factory().kind)))
        assert404(response)


class ReuseReferencesAPITest:
    modules = []

    def test_reuse_types_list(self, api):
        '''It should fetch the reuse types list from the API'''
        response = api.get(url_for('api.reuse_types'))
        assert200(response)
        assert len(response.json) == len(REUSE_TYPES)

    def test_reuse_topics_list(self, api):
        '''It should fetch the reuse topics list from the API'''
        response = api.get(url_for('api.reuse_topics'))
        assert200(response)
        assert len(response.json) == len(REUSE_TOPICS)
