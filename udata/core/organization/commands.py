# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import slugify

from udata.models import Dataset, DatasetBadge, User, C3
from udata.commands import manager


@manager.command
def add_c3_badges(filename):
    with open(filename, 'r') as titles:
        user = User.objects(first_name='Etalab', last_name='Bot').first()
        badge = DatasetBadge(kind=C3, created_by=user.id)
        for title in titles:
            title = title.decode('utf-8').strip(u'\n')
            if title.startswith(u'*'):
                continue
            slug = slugify.slugify(title.lower())
            dataset = (Dataset.objects(title=title).first()
                       or Dataset.objects(slug=slug).first())
            if dataset is None:
                print(title)
            else:
                dataset.badges.append(badge)
                dataset.save()
