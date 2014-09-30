# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from udata.frontend import render
from udata.i18n import I18nBlueprint
from udata.frontend.views import CreateView, EditView

from udata.models import Post

from .forms import PostForm
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
    return render('post/list.html', posts=Post.objects.order_by('-created_at'))


@blueprint.route('/<post:post>/')
def show(post):
    return render('post/display.html', post=post)


@blueprint.route('/new/', endpoint='new')
class PostCreateView(ProtectedPostView, CreateView):
    model = Post
    form = PostForm
    template_name = 'post/create.html'


@blueprint.route('/<post:post>/edit/', endpoint='edit')
class PostEditView(ProtectedPostView, EditView):
    form = PostForm
    template_name = 'post/edit.html'
