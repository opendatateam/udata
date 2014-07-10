# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from . import FrontTestCase
from udata.tests.factories import DatasetFactory, ReuseFactory, OrganizationFactory


class FrontEndRootTest(FrontTestCase):
    def test_render_home(self):
        '''It should render the home page'''
        with self.autoindex():
            for i in range(3):
                org = OrganizationFactory()
                DatasetFactory(organzation=org)
                ReuseFactory(organzation=org)

        response = self.get(url_for('front.home'))
        self.assert200(response)

    def test_render_home_no_data(self):
        '''It should render the home page without data'''
        response = self.get(url_for('front.home'))
        self.assert200(response)

    def test_render_search(self):
        '''It should render the search page'''
        with self.autoindex():
            for i in range(3):
                org = OrganizationFactory()
                DatasetFactory(organzation=org)
                ReuseFactory(organzation=org)

        response = self.get(url_for('front.search'))
        self.assert200(response)

    def test_render_search_no_data(self):
        '''It should render the search page without data'''
        response = self.get(url_for('front.search'))
        self.assert200(response)

    def test_render_explore(self):
        '''It should render the explore page'''
        with self.autoindex():
            for i in range(3):
                org = OrganizationFactory()
                DatasetFactory(organzation=org)
                ReuseFactory(organzation=org)

        response = self.get(url_for('front.explore'))
        self.assert200(response)

    def test_render_explore_empty(self):
        '''It should render the explore page even without data'''
        response = self.get(url_for('front.explore'))
        self.assert200(response)
