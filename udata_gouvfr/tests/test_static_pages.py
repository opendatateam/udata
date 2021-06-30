import pytest
import requests

from flask import url_for

from udata.app import cache
from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory
from udata_gouvfr.views.gouvfr import get_pages_gh_urls
from udata_gouvfr.tests import GouvFrSettings


@pytest.mark.usefixtures('clean_db')
class StaticPagesTest:
    settings = GouvFrSettings
    modules = []

    def test_page_does_not_exist(self, client, rmock):
        raw_url, gh_url = get_pages_gh_urls('doesnotexist')
        rmock.get(raw_url, status_code=404)
        response = client.get(url_for('gouvfr.show_page', slug='doesnotexist'))
        assert response.status_code == 404

    def test_page_error_no_cache(self, client, rmock):
        raw_url, gh_url = get_pages_gh_urls('doesnotexist')
        rmock.get(raw_url, status_code=500)
        response = client.get(url_for('gouvfr.show_page', slug='doesnotexist'))
        assert response.status_code == 503

    def test_page_timeout_no_cache(self, client, rmock):
        raw_url, gh_url = get_pages_gh_urls('doesnotexist')
        rmock.get(raw_url, exc=requests.exceptions.ConnectTimeout)
        response = client.get(url_for('gouvfr.show_page', slug='doesnotexist'))
        assert response.status_code == 503

    def test_page_error_w_cache(self, client, rmock, mocker):
        cache_mock_set = mocker.patch.object(cache, 'set')
        mocker.patch.object(cache, 'get', return_value='dummy_from_cache')
        raw_url, gh_url = get_pages_gh_urls('cache1')
        # fill cache
        rmock.get(raw_url, text="""#test""")
        response = client.get(url_for('gouvfr.show_page', slug='cache1'))
        assert cache_mock_set.called
        rmock.get(raw_url, status_code=500)
        response = client.get(url_for('gouvfr.show_page', slug='cache1'))
        assert response.status_code == 200
        assert b'dummy_from_cache' in response.data
        assert rmock.call_count == 2

    def test_page_error_empty_cache(self, client, rmock, mocker):
        mocker.patch.object(cache, 'get', return_value=None)
        raw_url, _ = get_pages_gh_urls('cache1')
        rmock.get(raw_url, status_code=500)
        response = client.get(url_for('gouvfr.show_page', slug='cache1'))
        assert response.status_code == 503

    def test_page(self, client, rmock):
        raw_url, _ = get_pages_gh_urls('test')
        rmock.get(raw_url, text="""#test""")
        response = client.get(url_for('gouvfr.show_page', slug='test'))
        assert response.status_code == 200
        assert b'<h1>test</h1>' in response.data

    def test_page_inject_empty_objects(self, client, rmock):
        raw_url, _ = get_pages_gh_urls('test')
        rmock.get(raw_url, text=f"""---
datasets:
reuses:
---
#test
""")
        response = client.get(url_for('gouvfr.show_page', slug='test'))
        assert response.status_code == 200

    def test_page_inject_objects(self, client, rmock):
        dataset = DatasetFactory()
        reuse = ReuseFactory()
        raw_url, _ = get_pages_gh_urls('test')
        rmock.get(raw_url, text=f"""---
datasets:
  - {dataset.id}
reuses:
  - {reuse.id}
---
#test
""")
        response = client.get(url_for('gouvfr.show_page', slug='test'))
        assert response.status_code == 200
        assert str(dataset.title).encode('utf-8') in response.data
        assert str(reuse.title).encode('utf-8') in response.data

    def test_page_subdir(self, client, rmock):
        raw_url, _ = get_pages_gh_urls('subdir/test')
        rmock.get(raw_url, text="""#test""")
        response = client.get(url_for('gouvfr.show_page', slug='subdir/test'))
        assert response.status_code == 200
        assert b'<h1>test</h1>' in response.data
