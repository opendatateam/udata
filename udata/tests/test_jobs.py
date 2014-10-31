# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.tests.frontend import FrontTestCase
from udata.tests.factories import AdminFactory


class JobsAdminTest(FrontTestCase):
    def test_render_jobs_empty(self):
        '''It should render the site jobs page'''
        self.login(AdminFactory())
        response = self.get(url_for('admin.jobs'))
        self.assert200(response)
