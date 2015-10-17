# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from udata import theme
from udata.i18n import I18nBlueprint

from udata.models import Post

from udata.sitemap import sitemap

from .permissions import PostEditPermission

blueprint = I18nBlueprint('posts', __name__, url_prefix='/posts')


class PostView(object):
    model = Post
    object_name = 'post'

    @property
    def _post(self):
        return self.get_object()


class ProtectedPostView(PostView):
    require = PostEditPermission()


@blueprint.route('/', endpoint='list')
def list_posts():
    return theme.render('post/list.html',
                        posts=Post.objects.order_by('-created_at'))


@blueprint.route('/<post:post>/')
def show(post):
    return theme.render('post/display.html', post=post)


@sitemap.register_generator
def sitemap_urls():
    for post in Post.objects(private=False).only('id', 'slug'):
        yield 'posts.show_redirect', {'post': post}, None, "weekly", 0.6
