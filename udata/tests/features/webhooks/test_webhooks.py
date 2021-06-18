import pytest

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
        'secret': 'mysecret',
    }, {
        'url': 'https://example.com/2',
        'secret': 'mysecret',
    }])
    def test_webhooks_from_settings(self, rmock):
        r1 = rmock.post('https://example.com/1', text='ok', status_code=200)
        r2 = rmock.post('https://example.com/2', text='ok', status_code=200)
        dispatch('event', {})
        assert r1.called
        assert r1.call_count == 1
        assert r2.called
        assert r2.call_count == 1

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


class WebhookIntegrationTest():
    pass
