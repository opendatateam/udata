# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from collections import Counter

from udata.commands import submanager, green, cyan, white
from udata.core.organization.models import Organization
from udata.core.post.models import Post
from udata.core.reuse.models import Reuse
from udata.core.user.models import User

log = logging.getLogger(__name__)


m = submanager(
    'images',
    help='Images related operations',
    description='Handle all images related operations and maintenance'
)


def render_or_skip(obj, attr):
    try:
        getattr(obj, attr).rerender()
        obj.save()
        return 1
    except Exception as e:
        log.warning('Skipped "%s": %s(%s)', obj, e.__class__.__name__, e)
        return 0


@m.command
def render():
    '''Force (re)rendering stored images'''
    print(cyan('Rendering images'))

    count = Counter()
    total = Counter()

    organizations = Organization.objects(logo__exists=True)
    total['orgs'] = organizations.count()
    print(white('Processing {0} organizations logos'.format(total['orgs'])))
    for org in organizations:
        count['orgs'] += render_or_skip(org, 'logo')

    users = User.objects(avatar__exists=True)
    total['users'] = users.count()
    print(white('Processing {0} user avatars'.format(total['users'])))
    for user in users:
        count['users'] += render_or_skip(user, 'avatar')

    posts = Post.objects(image__exists=True)
    total['posts'] = posts.count()
    print(white('Processing {0} post images'.format(total['posts'])))
    for post in posts:
        count['posts'] += render_or_skip(post, 'image')

    reuses = Reuse.objects(image__exists=True)
    total['reuses'] = reuses.count()
    print(white('Processing {0} reuse images'.format(total['reuses'])))
    for reuse in reuses:
        count['reuses'] += render_or_skip(reuse, 'image')

    print(white('Summary:'))
    print('''
    Organization logos: {count[orgs]}/{total[orgs]}
    User avatars: {count[users]}/{total[users]}
    Post images: {count[posts]}/{total[posts]}
    Reuse images: {count[reuses]}/{total[reuses]}
    '''.format(count=count, total=total))
    print(green('Images rendered'))
