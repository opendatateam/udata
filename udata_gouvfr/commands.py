# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import slugify

from udata.models import Dataset, DatasetBadge, User, C3
from udata.commands import submanager

log = logging.getLogger(__name__)


m = submanager('gouvfr',
    help='Data.gouv.fr specifics operations',
    description='Handle all Data.gouv.fr related operations and maintenance'
)


@m.command
def c3_badges(filename):
    '''Toggle C3 badges from an organization list'''
    with open(filename, 'r') as titles:
        user = User.objects(first_name='Etalab', last_name='Bot').first()
        badge = DatasetBadge(kind=C3, created_by=user)
        for title in titles:
            title = title.decode('utf-8').strip(u'\n')
            if title.startswith(u'*'):
                continue
            slug = slugify.slugify(title.lower())
            dataset = (Dataset.objects(title=title).first()
                       or Dataset.objects(slug=slug).first())
            if dataset is None:
                log.info(u'{title} not found'.format(title=title))
            else:
                dataset.badges.append(badge)
                dataset.save()
    log.info('Done')
