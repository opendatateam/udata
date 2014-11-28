# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from bson import ObjectId

from datetime import datetime

from flask import abort, request, url_for, redirect, render_template, flash
from werkzeug.contrib.atom import AtomFeed

from udata.app import nav
from udata.forms import ReuseForm, ReuseCreateForm, AddDatasetToReuseForm
from udata.frontend.views import SearchView, DetailView, CreateView, EditView, SingleObject, BaseView
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.models import Reuse, Issue, FollowReuse, Dataset

from .permissions import ReuseEditPermission, set_reuse_identity
from .tasks import notify_new_reuse

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
                'uri': url_for('organizations.show', org=reuse.organization.id, _external=True),
            }
        elif reuse.owner:
            author = {
                'name': reuse.owner.fullname,
                'uri': url_for('users.show', user=reuse.owner.id, _external=True),
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
    nav.Item(_('Descrition'), 'reuses.edit'),
    nav.Item(_('Issues'), 'reuses.issues'),
    nav.Item(_('Transfer'), 'reuses.transfer'),
])


class ReuseView(object):
    model = Reuse
    object_name = 'reuse'

    @property
    def reuse(self):
        return self.get_object()

    def set_identity(self, identity):
        set_reuse_identity(identity, self.reuse)

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

        followers = FollowReuse.objects.followers(self.reuse).order_by('follower.fullname')

        context.update(
            followers=followers,
            can_edit=ReuseEditPermission(self.reuse)
        )

        return context


@blueprint.route('/new/', endpoint='new')
class ReuseCreateView(CreateView):
    model = Reuse
    form = ReuseCreateForm
    template_name = 'reuse/create.html'

    def initialize_form(self, form):
        if 'dataset' in request.args:
            try:
                dataset = Dataset.objects.get(id=request.args['dataset'])
                form.datasets.data = [dataset]
            except:
                pass
        return form

    def on_form_valid(self, form):
        response = super(ReuseCreateView, self).on_form_valid(form)
        notify_new_reuse.delay(self.object)
        return response


@blueprint.route('/<reuse:reuse>/edit/', endpoint='edit')
class ReuseEditView(ProtectedReuseView, EditView):
    form = ReuseForm
    template_name = 'reuse/edit.html'


@blueprint.route('/<reuse:reuse>/add/', endpoint='add_dataset')
class ReuseAddDatasetView(ProtectedReuseView, SingleObject, BaseView):
    def post(self, reuse):
        form = AddDatasetToReuseForm(request.form)
        if form.validate():
            try:
                dataset = Dataset.objects.get(id=ObjectId(form.dataset.data))
                if dataset not in self.reuse.datasets:
                    self.reuse.datasets.append(dataset)
                    self.reuse.save()
                    flash(_('The dataset "%(title)s" has been added to the reuse', title=dataset.title), 'success')
                return redirect(url_for('reuses.show', reuse=self.reuse))
            except:
                pass
        return redirect(url_for('reuses.edit', reuse=self.reuse))


@blueprint.route('/<reuse:reuse>/delete/', endpoint='delete')
class ReuseDeleteView(ProtectedReuseView, SingleObject, BaseView):
    def post(self, reuse):
        reuse.deleted = datetime.now()
        reuse.save()
        return redirect(url_for('reuses.show', reuse=self.reuse))


@blueprint.route('/<reuse:reuse>/issues/', endpoint='issues')
class ReuseIssuesView(ProtectedReuseView, DetailView):
    template_name = 'reuse/issues.html'

    def get_context(self):
        context = super(ReuseIssuesView, self).get_context()
        context['issues'] = Issue.objects(subject=self.reuse)
        return context


@blueprint.route('/<reuse:reuse>/transfer/', endpoint='transfer')
class ReuseTransferView(ProtectedReuseView, EditView):
    form = ReuseForm
    template_name = 'reuse/transfer.html'
