from flask import abort, request, url_for
from werkzeug.contrib.atom import AtomFeed

from udata.app import nav
from udata.frontend.views import SearchView, DetailView
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.models import Follow
from udata.sitemap import sitemap
from udata.theme import render as render_template

from .models import Reuse
from .permissions import ReuseEditPermission

blueprint = I18nBlueprint('reuses', __name__, url_prefix='/reuses')


@blueprint.route('/recent.atom')
def recent_feed():
    feed = AtomFeed(_('Last reuses'),
                    feed_url=request.url, url=request.url_root)
    reuses = Reuse.objects.visible().order_by('-created_at').limit(15)
    for reuse in reuses:
        author = None
        if reuse.organization:
            author = {
                'name': reuse.organization.name,
                'uri': url_for('organizations.show',
                               org=reuse.organization.id, _external=True),
            }
        elif reuse.owner:
            author = {
                'name': reuse.owner.fullname,
                'uri': url_for('users.show',
                               user=reuse.owner.id, _external=True),
            }
        feed.add(reuse.title,
                 render_template('reuse/feed_item.html', reuse=reuse),
                 content_type='html',
                 author=author,
                 url=url_for('reuses.show', reuse=reuse.id, _external=True),
                 updated=reuse.created_at,
                 published=reuse.created_at)
    return feed.get_response()


@blueprint.route('/', endpoint='list')
class ReuseListView(SearchView):
    model = Reuse
    context_name = 'reuses'
    template_name = 'reuse/list.html'


navbar = nav.Bar('edit_reuse', [
    nav.Item(_('Issues'), 'reuses.issues'),
    nav.Item(_('Transfer'), 'reuses.transfer'),
])


class ReuseView(object):
    model = Reuse
    object_name = 'reuse'

    @property
    def reuse(self):
        return self.get_object()

    def get_context(self):
        for item in navbar:
            item._args = {'reuse': self.reuse}
        return super(ReuseView, self).get_context()


class ProtectedReuseView(ReuseView):
    def can(self, *args, **kwargs):
        permission = ReuseEditPermission(self.reuse)
        return permission.can()


@blueprint.route('/<reuse:reuse>/', endpoint='show')
class ReuseDetailView(ReuseView, DetailView):
    template_name = 'reuse/display.html'

    def get_context(self):
        context = super(ReuseDetailView, self).get_context()

        if self.reuse.private and not ReuseEditPermission(self.reuse).can():
            abort(404)

        if self.reuse.deleted and not ReuseEditPermission(self.reuse).can():
            abort(410)

        followers = (Follow.objects.followers(self.reuse)
                     .order_by('follower.fullname'))

        context.update(
            followers=followers,
            can_edit=ReuseEditPermission(self.reuse),
        )

        return context


@sitemap.register_generator
def sitemap_urls():
    for reuse in Reuse.objects.visible().only('id', 'slug'):
        yield 'reuses.show_redirect', {'reuse': reuse}, None, 'weekly', 0.8
