# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.tests.frontend import FrontTestCase
from udata.tests.factories import AdminFactory


class SiteAdminViewTest(FrontTestCase):
    def test_render_issues_empty(self):
        '''It should render the dataset issues'''
        self.login(AdminFactory())
        response = self.get(url_for('site.issues'))
        self.assert200(response)
