# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from udata.frontend import render
from udata.i18n import I18nBlueprint

from udata.models import Post

blueprint = I18nBlueprint('posts', __name__, url_prefix='/posts')


@blueprint.route('/', endpoint='list')
def list_posts():
    return render('post/list.html', posts=Post.objects.order_by('-created_at'))


@blueprint.route('/<post:post>/')
def show(post):
    return render('post/display.html', post=post)
