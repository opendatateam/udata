# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.organization.factories import OrganizationFactory

from udata.tests.helpers import assert200


class SearchFrontTest:
    modules = ['core.dataset', 'core.reuse', 'core.organization',
               'admin', 'core.site', 'search']

    def test_render_search(self, client, autoindex):
        '''It should render the search page'''
        with autoindex():
            for i in range(3):
                org = OrganizationFactory()
                DatasetFactory(organization=org)
                ReuseFactory(organization=org)

        response = client.get(url_for('search.index'))
        assert200(response)

    def test_render_search_no_data(self, client, autoindex):
        '''It should render the search page without data'''
        response = client.get(url_for('search.index'))
        assert200(response)

    def test_render_search_wihtout_xss(self, client, autoindex):
        '''It should render the search page without data'''
        xss = '/><script src="whatever.js">'
        response = client.get(url_for('search.index', tag=xss))
        assert200(response)
        assert xss not in response.data.decode('utf8')
