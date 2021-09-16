from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata_front.tests import GouvFrSettings
from udata_front.tests.frontend import GouvfrFrontTestCase


class SecurityViewsTest(GouvfrFrontTestCase):
    settings = GouvFrSettings

    def test_security_login_next_home(self):
        '''Login should redirect to the correct next endpoint: homepage'''
        response = self.get(url_for('site.home'))
        assert b'<a href="/en/login?next=%2Fen%2F"' in response.data

    def test_security_login_next_datasets(self):
        '''Login should redirect to the correct next endpoint: dataset'''
        dataset = DatasetFactory(slug="dataset-slug")
        response = self.get(url_for('datasets.show', dataset=dataset))
        assert b'<a href="/en/login?next=%2Fen%2Fdatasets%2Fdataset-slug%2F"' in response.data

    def test_security_login_next_exception_site_home(self):
        '''Login should redirect to the homepage if current request has an exception'''
        response = self.get(url_for('datasets.show', dataset='dataset-not-found'))
        assert b'<a href="/en/login?next=%2Fen%2F"' in response.data
