# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from udata.commands import submanager
from udata.linkchecker.tasks import check_resources


log = logging.getLogger(__name__)

m = submanager('linkchecker',
               help='Link checking operations',
               description='Handle link checking operations'
               )


@m.option('-n', '--number', type=int, dest='number', default=5000,
          help='Number of URLs to check')
def check(number):
    '''Check <number> of URLs that have not been (recently) checked'''
    check_resources(number)
