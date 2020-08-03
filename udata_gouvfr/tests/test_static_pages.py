import pytest
import requests

from flask import url_for

from udata.app import cache
from udata_gouvfr.views import get_pages_gh_urls
from udata_gouvfr.tests.tests import GouvFrSettings


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
        raw_url, gh_url = get_pages_gh_urls('cache1')
        rmock.get(raw_url, status_code=500)
        response = client.get(url_for('gouvfr.show_page', slug='cache1'))
        assert response.status_code == 503

    def test_page(self, client, rmock):
        raw_url, gh_url = get_pages_gh_urls('test')
        rmock.get(raw_url, text="""#test""")
        response = client.get(url_for('gouvfr.show_page', slug='test'))
        assert response.status_code == 200
        assert b'<h1>test</h1>' in response.data
