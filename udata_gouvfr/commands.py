# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import slugify
from os.path import exists

from udata.models import Dataset, DatasetBadge, User, C3
from udata.commands import manager
from udata.models import Organization, OrganizationBadge

log = logging.getLogger(__name__)


def toggle(id_or_slug, badge_kind):
    organization = Organization.objects.get_by_id_or_slug(id_or_slug)
    if not organization:
        print 'No organization found for {0}'.format(id_or_slug)
        return
    print 'Toggling badge {kind} for organization {org}'.format(
        kind=badge_kind,
        org=organization.name
    )
    existed = False
    for badge in organization.badges:
        if badge.kind == badge_kind:
            organization.badges.remove(badge)
            existed = True
            break
    if not existed:
        badge = OrganizationBadge(kind=badge_kind)
        organization.badges.append(badge)
    organization.save()


@manager.command
def toggle_badge(path_or_id, badge_kind):
    '''Toggle a `badge_kind` for a given `path_or_id`

    The `path_or_id` is either an id, a slug or a file containing a list
    of ids or slugs.
    '''
    if exists(path_or_id):
        with open(path_or_id) as open_file:
            for id_or_slug in open_file.readlines():
                toggle(id_or_slug.strip(), badge_kind)
    else:
        toggle(path_or_id, badge_kind)


@manager.command
def add_c3_badges(filename):
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
