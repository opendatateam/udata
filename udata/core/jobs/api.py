# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.api import api, API, refs
from udata.tasks import schedulables


@api.route('/jobs/')
class JobsAPI(API):
    def get(self):
        return {}


@refs.route('/jobs', endpoint='schedulable_jobs')
class JobsReferenceAPI(API):
    @api.doc(model=[str])
    def get(self):
        '''List all schedulable jobs'''
        return [job.name for job in schedulables()]
