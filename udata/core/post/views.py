from flask import current_app

from udata import theme
from udata.frontend.views import ListView
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
class PostListView(ListView):
    model = Post
    template_name = 'post/list.html'
    context_name = 'posts'

    @property
    def default_page_size(self):
        return current_app.config['POST_DEFAULT_PAGINATION']

    def get_queryset(self):
        return Post.objects.published().paginate(self.page, self.page_size)


@blueprint.route('/<post:post>/')
def show(post):
    others = Post.objects(id__ne=post.id).published()
    older = others(published__lt=post.published).order_by('-published')
    newer = others(published__gt=post.published).order_by('published')
    return theme.render('post/display.html',
                        post=post,
                        previous_post=older.first(),
                        next_post=newer.first())


@sitemap.register_generator
def sitemap_urls():
    yield 'posts.list_redirect', {}, None, "weekly", 0.6
    for post in Post.objects.published().only('id', 'slug'):
        yield 'posts.show_redirect', {'post': post}, None, "weekly", 0.6
