# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import request, url_for, g
from werkzeug.contrib.atom import AtomFeed

from udata.forms import ReuseForm
from udata.frontend.views import SearchView, DetailView, CreateView, EditView
from udata.i18n import I18nBlueprint
from udata.models import Reuse, REUSE_TYPES
from udata.search import ReuseSearch

from .permissions import ReuseEditPermission, set_reuse_identity

blueprint = I18nBlueprint('reuses', __name__, url_prefix='/reuses')


@blueprint.before_app_request
def store_references_lists():
    g.reuse_types = REUSE_TYPES


@blueprint.route('/recent.atom')
def recent_feed():
    feed = AtomFeed('Recent Articles',
                    feed_url=request.url, url=request.url_root)
    datasets = Reuse.objects.order_by('-date').limit(15)
    for dataset in datasets:
        author = None
        if dataset.organization:
            author = {
                'name': dataset.organization.name,
                'uri': url_for('organizations.show', org=dataset.organization, _external=True),
            }
        elif dataset.owner:
            author = {
                'name': dataset.owner.fullname,
                'uri': url_for('users.show', user=dataset.owner, _external=True),
            }
        feed.add(dataset.title, dataset.description,
                 content_type='html',
                 author=author,
                 url=url_for('datasets.show', dataset=dataset, _external=True),
                 updated=dataset.created_at,
                 published=dataset.created_at)
    return feed.get_response()


class ReuseListView(SearchView):
    model = Reuse
    context_name = 'reuses'
    template_name = 'reuse/list.html'
    search_adapter = ReuseSearch
    search_endpoint = 'reuses.list'


class ReuseView(object):
    model = Reuse
    object_name = 'reuse'

    @property
    def reuse(self):
        return self.get_object()

    def set_identity(self, identity):
        set_reuse_identity(identity, self.reuse)


class ProtectedReuseView(ReuseView):
    def can(self, *args, **kwargs):
        permission = ReuseEditPermission(self.reuse)
        return permission.can()


class ReuseDetailView(ReuseView, DetailView):
    template_name = 'reuse/display.html'


class ReuseCreateView(CreateView):
    model = Reuse
    form = ReuseForm
    template_name = 'reuse/create.html'


class ReuseEditView(ProtectedReuseView, EditView):
    form = ReuseForm
    template_name = 'reuse/edit.html'


blueprint.add_url_rule('/', view_func=ReuseListView.as_view(str('list')))
blueprint.add_url_rule('/new/', view_func=ReuseCreateView.as_view(str('new')))
blueprint.add_url_rule('/<reuse:reuse>/', view_func=ReuseDetailView.as_view(str('show')))
blueprint.add_url_rule('/<reuse:reuse>/edit/', view_func=ReuseEditView.as_view(str('edit')))
