# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.organization.factories import OrganizationFactory

from . import FrontTestCase


class FrontEndRootTest(FrontTestCase):
    def test_render_search(self):
        '''It should render the search page'''
        with self.autoindex():
            for i in range(3):
                org = OrganizationFactory()
                DatasetFactory(organization=org)
                ReuseFactory(organization=org)

        response = self.get(url_for('front.search'))
        self.assert200(response)

    def test_render_search_no_data(self):
        '''It should render the search page without data'''
        self.init_search()
        response = self.get(url_for('front.search'))
        self.assert200(response)
