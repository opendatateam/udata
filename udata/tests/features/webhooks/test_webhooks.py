from datetime import datetime

import pytest

from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.discussions.factories import DiscussionFactory, MessageDiscussionFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import UserFactory
from udata.features.webhooks.tasks import dispatch, _dispatch
from udata.features.webhooks.utils import sign

pytestmark = pytest.mark.usefixtures('clean_db')


class WebhookUnitTest():

    @pytest.mark.options(WEBHOOKS=[])
    def test_no_webhooks(self):
        dispatch('event', {})
        assert True

    def test_webhooks_task(self, rmock):
        '''NB: apparently celery task errors don't surface so we need to test them directly'''
        r = rmock.post('https://example.com', text='ok', status_code=200)
        _dispatch('event', {'tada': 'dam'}, {
            'url': 'https://example.com',
            'secret': 'mysecret',
        })
        assert r.called
        assert r.call_count == 1
        res = r.last_request
        payload = {
            'event': 'event',
            'payload': {'tada': 'dam'},
        }
        assert res.headers.get('x-hook-signature') == sign(payload, 'mysecret')
        assert res.json() == payload

    @pytest.mark.options(WEBHOOKS=[{
        'url': 'https://example.com/1',
        'events': ['event'],
        'secret': 'mysecret',
    }, {
        'url': 'https://example.com/2',
        'events': ['event'],
        'secret': 'mysecret',
    }, {
        'url': 'https://example.com/3',
        'events': ['notmyevent'],
        'secret': 'mysecret',
    }])
    def test_webhooks_from_settings(self, rmock):
        r1 = rmock.post('https://example.com/1', text='ok', status_code=200)
        r2 = rmock.post('https://example.com/2', text='ok', status_code=200)
        r3 = rmock.post('https://example.com/3', text='ok', status_code=200)
        dispatch('event', {})
        assert r1.called
        assert r1.call_count == 1
        assert r2.called
        assert r2.call_count == 1
        assert not r3.called

    @pytest.mark.skip(reason="""
        I really tried but no luck :-(
        (pytest-celery, using requests Retry instead of Celery's...)
        Made it work in real life on 2021-06-18 (true story)
    """)
    @pytest.mark.options(WEBHOOKS=[{
        'url': 'https://example.com/3',
        'secret': 'mysecret',
    }])
    def test_webhooks_retry(self, rmock):
        r = rmock.post('https://example.com/3', text='ko', status_code=500)
        dispatch('event', {'tada': 'dam'})
        assert r.called
        assert r.call_count == 3


@pytest.mark.options(WEBHOOKS=[{
    'url': 'https://example.com/publish',
    'events': [
        'datagouvfr.dataset.created',
        'datagouvfr.dataset.updated',
        'datagouvfr.dataset.deleted',
        'datagouvfr.discussion.created',
        'datagouvfr.discussion.closed',
        'datagouvfr.discussion.commented',
        'datagouvfr.organization.created',
        'datagouvfr.organization.updated',
        'datagouvfr.reuse.created',
        'datagouvfr.reuse.updated',
    ],
    'secret': 'mysecret',
}])
class WebhookIntegrationTest():
    modules = []
    # plug the signals in for tests
    from udata.features.webhooks import triggers  # noqa

    @pytest.fixture
    def rmock_pub(self, rmock):
        return rmock.post('https://example.com/publish', text='ok', status_code=201)

    def test_dataset_create(self, rmock_pub):
        ds = DatasetFactory()
        assert rmock_pub.called
        res = rmock_pub.last_request.json()
        assert res['event'] == 'datagouvfr.dataset.created'
        assert res['payload']['title'] == ds['title']

    def test_dataset_update(self, rmock_pub):
        ds = DatasetFactory()
        ds.title = 'newtitle'
        ds.save()
        assert rmock_pub.called
        res = rmock_pub.last_request.json()
        assert res['event'] == 'datagouvfr.dataset.updated'
        assert res['payload']['title'] == 'newtitle'

    def test_dataset_delete(self, rmock_pub):
        ds = DatasetFactory()
        ds.deleted = datetime.now()
        ds.save()
        assert rmock_pub.called
        res = rmock_pub.last_request.json()
        assert res['event'] == 'datagouvfr.dataset.deleted'
        assert res['payload']['title'] == ds['title']

    def test_discussion_created(self, rmock_pub, api):
        dataset = DatasetFactory()

        api.login()
        response = api.post(url_for('api.discussions'), {
            'title': 'test title',
            'comment': 'bla bla',
            'subject': {
                'class': 'Dataset',
                'id': dataset.id,
            }
        })
        assert response.status_code == 201

        assert rmock_pub.called
        res = rmock_pub.last_request.json()
        assert res['event'] == 'datagouvfr.discussion.created'
        assert res['payload']['title'] == 'test title'

    def test_discussion_commented(self, rmock_pub, api):
        dataset = DatasetFactory()
        user = UserFactory()
        message = MessageDiscussionFactory(content='bla bla', posted_by=user)
        discussion = DiscussionFactory(
            subject=dataset,
            user=user,
            title='test discussion',
            discussion=[message]
        )

        api.login()
        response = api.post(url_for('api.discussion', id=discussion.id), {
            'comment': 'new bla bla'
        })
        assert response.status_code == 200

        assert rmock_pub.called
        res = rmock_pub.last_request.json()
        assert res['event'] == 'datagouvfr.discussion.commented'
        assert res['payload']['message_id'] == 1
        assert res['payload']['discussion']['title'] == 'test discussion'
        assert res['payload']['discussion']['discussion'][1]['content'] == 'new bla bla'

    def test_discussion_closed(self, rmock_pub, api):
        owner = api.login()
        user = UserFactory()
        dataset = DatasetFactory(title='Test dataset', owner=owner)
        message = MessageDiscussionFactory(content='bla bla', posted_by=user)
        discussion = DiscussionFactory(
            subject=dataset,
            user=user,
            title='test discussion',
            discussion=[message]
        )

        response = api.post(url_for('api.discussion', id=discussion.id), {
            'comment': 'close bla bla',
            'close': True
        })
        assert response.status_code == 200

        assert rmock_pub.called
        res = rmock_pub.last_request.json()
        assert res['event'] == 'datagouvfr.discussion.closed'
        assert res['payload']['message_id'] == 1
        assert res['payload']['discussion']['title'] == 'test discussion'
        assert res['payload']['discussion']['discussion'][1]['content'] == 'close bla bla'

    def test_organization_create(self, rmock_pub):
        org = OrganizationFactory()
        assert rmock_pub.called
        res = rmock_pub.last_request.json()
        assert res['event'] == 'datagouvfr.organization.created'
        assert res['payload']['name'] == org['name']

    def test_organization_update(self, rmock_pub):
        org = OrganizationFactory()
        org.name = 'newtitle'
        org.save()
        assert rmock_pub.called
        res = rmock_pub.last_request.json()
        assert res['event'] == 'datagouvfr.organization.updated'
        assert res['payload']['name'] == 'newtitle'

    def test_reuse_create(self, rmock_pub):
        reuse = ReuseFactory()
        assert rmock_pub.called
        res = rmock_pub.last_request.json()
        assert res['event'] == 'datagouvfr.reuse.created'
        assert res['payload']['title'] == reuse['title']

    def test_reuse_update(self, rmock_pub):
        reuse = ReuseFactory()
        reuse.title = 'newtitle'
        reuse.save()
        assert rmock_pub.called
        res = rmock_pub.last_request.json()
        assert res['event'] == 'datagouvfr.reuse.updated'
        assert res['payload']['title'] == 'newtitle'
