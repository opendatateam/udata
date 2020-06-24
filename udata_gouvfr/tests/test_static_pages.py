import pytest

from flask import url_for

from udata_gouvfr.views import get_pages_gh_urls
from .tests import GouvFrSettings


@pytest.mark.usefixtures('clean_db')
class StaticPagesTest:
    settings = GouvFrSettings
    modules = []

    def test_page_does_not_exist(self, client, rmock):
        raw_url, gh_url = get_pages_gh_urls('doesnotexist')
        rmock.get(raw_url, status_code=404)
        response = client.get(url_for('gouvfr.show_page', slug='doesnotexist'))
        assert response.status_code == 404

    def test_page(self, client, rmock):
        raw_url, gh_url = get_pages_gh_urls('test')
        rmock.get(raw_url, text="""#test""")
        response = client.get(url_for('gouvfr.show_page', slug='test'))
        assert response.status_code == 200
        assert b'<h1>test</h1>' in response.data
