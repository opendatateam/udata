# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from flask import abort, redirect, request, url_for
from werkzeug.contrib.atom import AtomFeed

from udata.forms import DatasetForm, ResourceForm
from udata.frontend.views import ListView, DetailView, CreateView, EditView, SingleObject
from udata.i18n import I18nBlueprint
from udata.models import Dataset, Resource, Reuse, UPDATE_FREQUENCIES
from udata.search import DatasetSearch

from .permissions import DatasetEditPermission, set_dataset_identity

blueprint = I18nBlueprint('datasets', __name__, url_prefix='/datasets')


@blueprint.route('/recent.atom')
def recent_feed():
    feed = AtomFeed('Recent Articles',
                    feed_url=request.url, url=request.url_root)
    datasets = Dataset.objects.order_by('-date').limit(15)
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
                 updated=dataset.last_modified,
                 published=dataset.created_at)
    return feed.get_response()


class DatasetListView(ListView):
    model = Dataset
    context_name = 'datasets'
    template_name = 'dataset/list.html'
    search_adapter = DatasetSearch


class DatasetView(object):
    model = Dataset
    object_name = 'dataset'

    @property
    def dataset(self):
        return self.get_object()

    def set_identity(self, identity):
        set_dataset_identity(identity, self.dataset)


class ProtectedDatasetView(DatasetView):
    def can(self, *args, **kwargs):
        permission = DatasetEditPermission(self.dataset)
        return permission.can()


class DatasetDetailView(DatasetView, DetailView):
    template_name = 'dataset/display.html'

    def get_context(self):
        context = super(DatasetDetailView, self).get_context()
        context['reuses'] = Reuse.objects(datasets=self.dataset)
        context['can_edit'] = DatasetEditPermission(self.dataset)
        context['UPDATE_FREQUENCIES'] = UPDATE_FREQUENCIES
        return context


class DatasetCreateView(CreateView):
    model = Dataset
    form = DatasetForm
    template_name = 'dataset/create.html'


class DatasetEditView(ProtectedDatasetView, EditView):
    form = DatasetForm
    template_name = 'dataset/edit.html'


class ResourceCreateView(SingleObject, CreateView):
    model = Dataset
    form = ResourceForm
    object_name = 'dataset'
    template_name = 'dataset/resource/create.html'

    def on_form_valid(self, form):
        resource = Resource()
        form.populate_obj(resource)
        self.object.resources.append(resource)
        self.object.save()
        return redirect(url_for('datasets.show', dataset=self.object))


class ResourceEditView(EditView):
    model = Resource
    form = ResourceForm
    object_name = 'resource'
    template_name = 'dataset/resource/edit.html'

    def get_object(self):
        if not self.object:
            self.dataset = self.kwargs['dataset']
            rid = self.kwargs.get('rid')
            for resource in self.dataset.resources:
                if str(resource.id) == rid:
                    self.object = resource
                    break
            else:
                abort(404, 'Resource {0} does not exists in dataset'.format(rid))
        return self.object

    def get_context(self):
        context = super(ResourceEditView, self).get_context()
        context['dataset'] = self.dataset
        return context

    def on_form_valid(self, form):
        form.populate_obj(self.object)
        self.dataset.save()
        return redirect(url_for('datasets.show', dataset=self.dataset))


blueprint.add_url_rule('/', view_func=DatasetListView.as_view(str('list')))
blueprint.add_url_rule('/new/', view_func=DatasetCreateView.as_view(str('new')))
blueprint.add_url_rule('/<dataset:dataset>/', view_func=DatasetDetailView.as_view(str('show')))
blueprint.add_url_rule('/<dataset:dataset>/edit/', view_func=DatasetEditView.as_view(str('edit')))
blueprint.add_url_rule('/<dataset:dataset>/resources/new/', view_func=ResourceCreateView.as_view(str('new_resource')))
blueprint.add_url_rule('/<dataset:dataset>/resources/<rid>/', view_func=ResourceEditView.as_view(str('edit_resource')))
