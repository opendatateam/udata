# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import abort, redirect, request, url_for, g, jsonify, render_template
from werkzeug.contrib.atom import AtomFeed

from udata import fileutils
from udata.auth import login_required
from udata.forms import DatasetForm, DatasetCreateForm, ResourceForm, CommunityResourceForm, DatasetExtraForm
from udata.frontend import nav
from udata.frontend.views import DetailView, CreateView, EditView, NestedEditView, SingleObject, SearchView, BaseView, NestedObject
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.models import Dataset, Resource, Reuse, Issue, Follow

from udata.core import storages
from udata.core.site.views import current_site

from .permissions import CommunityResourceEditPermission, DatasetEditPermission, set_dataset_identity

blueprint = I18nBlueprint('datasets', __name__, url_prefix='/datasets')


@blueprint.route('/recent.atom')
def recent_feed():
    feed = AtomFeed(_('Last datasets'),
                    feed_url=request.url, url=request.url_root)
    datasets = Dataset.objects.visible().order_by('-created_at').limit(current_site.feed_size)
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
        feed.add(dataset.title,
                render_template('dataset/feed_item.html', dataset=dataset),
                content_type='html',
                author=author,
                url=url_for('datasets.show', dataset=dataset, _external=True),
                updated=dataset.last_modified,
                published=dataset.created_at)
    return feed.get_response()


@blueprint.route('/', endpoint='list')
class DatasetListView(SearchView):
    model = Dataset
    context_name = 'datasets'
    template_name = 'dataset/list.html'


navbar = nav.Bar('edit_dataset', [
    nav.Item(_('Descrition'), 'datasets.edit'),
    nav.Item(_('Additionnal informations'), 'datasets.edit_extras'),
    nav.Item(_('Resources'), 'datasets.edit_resources'),
    nav.Item(_('Issues'), 'datasets.issues'),
    nav.Item(_('Transfer'), 'datasets.transfer'),
])


class DatasetView(object):
    model = Dataset
    object_name = 'dataset'

    @property
    def dataset(self):
        return self.get_object()

    def set_identity(self, identity):
        set_dataset_identity(identity, self.dataset)

    def get_context(self):
        for item in navbar:
            item._args = {'dataset': self.dataset}
        return super(DatasetView, self).get_context()


class ProtectedDatasetView(DatasetView):
    def can(self, *args, **kwargs):
        permission = DatasetEditPermission(self.dataset)
        return permission.can()


@blueprint.route('/<dataset:dataset>/', endpoint='show')
class DatasetDetailView(DatasetView, DetailView):
    template_name = 'dataset/display.html'

    def get_context(self):
        context = super(DatasetDetailView, self).get_context()
        if self.dataset.private and not DatasetEditPermission(self.dataset).can():
            abort(404)
        context['reuses'] = Reuse.objects(datasets=self.dataset)
        context['can_edit'] = DatasetEditPermission(self.dataset)
        context['can_edit_resource'] = CommunityResourceEditPermission
        return context


@blueprint.route('/new/', endpoint='new')
class DatasetCreateView(CreateView):
    model = Dataset
    form = DatasetCreateForm
    template_name = 'dataset/create.html'

    def get_success_url(self):
        return url_for('datasets.new_resource', dataset=self.object)


@blueprint.route('/<dataset:dataset>/edit/', endpoint='edit')
class DatasetEditView(ProtectedDatasetView, EditView):
    form = DatasetForm
    template_name = 'dataset/edit.html'


@blueprint.route('/<dataset:dataset>/delete/', endpoint='delete')
class DatasetDeleteView(ProtectedDatasetView, SingleObject, BaseView):
    def post(self, dataset):
        dataset.deleted = datetime.now()
        dataset.save()
        return redirect(url_for('datasets.show', dataset=self.dataset))


@blueprint.route('/<dataset:dataset>/edit/extras/', endpoint='edit_extras')
class DatasetExtrasEditView(ProtectedDatasetView, EditView):
    form = DatasetExtraForm
    template_name = 'dataset/edit_extras.html'

    def on_form_valid(self, form):
        if form.old_key.data:
            del self.dataset.extras[form.old_key.data]
        self.dataset.extras[form.key.data] = form.value.data
        self.dataset.save()
        return jsonify({'key': form.key.data, 'value': form.value.data})


@blueprint.route('/<dataset:dataset>/edit/extras/<string:extra>/', endpoint='delete_extra')
class DatasetExtraDeleteView(ProtectedDatasetView, SingleObject, BaseView):
    def delete(self, dataset, extra, **kwargs):
        del dataset.extras[extra]
        dataset.save()
        return ''


@blueprint.route('/<dataset:dataset>/edit/resources/', endpoint='edit_resources')
class DatasetResourcesEditView(ProtectedDatasetView, EditView):
    form = DatasetForm
    template_name = 'dataset/edit_resources.html'


@blueprint.route('/<dataset:dataset>/issues/', endpoint='issues')
class DatasetIssuesView(ProtectedDatasetView, DetailView):
    template_name = 'dataset/issues.html'

    def get_context(self):
        context = super(DatasetIssuesView, self).get_context()
        context['issues'] = Issue.objects(subject=self.dataset)
        return context


@blueprint.route('/<dataset:dataset>/transfer/', endpoint='transfer')
class DatasetTransferView(ProtectedDatasetView, EditView):
    form = DatasetForm
    template_name = 'dataset/transfer.html'


@blueprint.route('/<dataset:dataset>/resources/new/', endpoint='new_resource')
class ResourceCreateView(ProtectedDatasetView, SingleObject, CreateView):
    form = ResourceForm
    template_name = 'dataset/resource/create.html'

    def on_form_valid(self, form):
        resource = Resource()
        form.populate_obj(resource)
        self.object.resources.append(resource)
        self.object.save()
        return redirect(url_for('datasets.show', dataset=self.object))


class UploadNewResource(SingleObject, BaseView):
    def post(self, dataset):
        if not 'file' in request.files:
            return jsonify({'success': False, 'error': '"file" should be set'}), 400

        storage = storages.resources

        prefix = self.get_prefix(dataset)

        file = request.files['file']
        filename = storage.save(file, prefix=prefix)

        extension = fileutils.extension(filename)

        file.seek(0)
        sha1 = storages.utils.sha1(file)

        return jsonify({
            'success': True,
            'url': storage.url(filename),
            'filename': filename,
            'sha1': sha1,
            'format': extension,
            'size': file.content_length
        })

    def get_prefix(self, dataset):
        return '/'.join((dataset.slug, datetime.now().strftime('%Y%m%d-%H%M%S')))


@blueprint.route('/<dataset:dataset>/resources/new/upload', endpoint='upload_new_resource')
class UploadNewResourceView(ProtectedDatasetView, UploadNewResource):
    '''Handle upload on POST if authorized.'''
    pass


@blueprint.route('/<dataset:dataset>/community_resources/new/upload', endpoint='upload_new_community_resource')
class UploadNewCommunityResourceView(DatasetView, UploadNewResource):
    '''Handle upload on POST if authorized.'''
    decorators = [login_required]

    def get_prefix(self, dataset):
        return '/'.join((dataset.slug, 'community', datetime.now().strftime('%Y%m%d-%H%M%S')))


@blueprint.route('/<dataset:dataset>/community_resources/new/', endpoint='new_community_resource')
class CommunityResourceCreateView(DatasetView, SingleObject, CreateView):
    form = CommunityResourceForm
    template_name = 'dataset/resource/create.html'

    def on_form_valid(self, form):
        resource = Resource()
        form.populate_obj(resource)
        self.object.community_resources.append(resource)
        self.object.save()
        return redirect(url_for('datasets.show', dataset=self.object))


@blueprint.route('/<dataset:dataset>/resources/<resource>/', endpoint='edit_resource')
class ResourceEditView(ProtectedDatasetView, NestedEditView):
    nested_model = Resource
    form = ResourceForm
    nested_object_name = 'resource'
    nested_attribute = 'resources'
    template_name = 'dataset/resource/edit.html'

    def get_success_url(self):
        return url_for('datasets.show', dataset=self.dataset)


@blueprint.route('/<dataset:dataset>/community_resources/<resource>/', endpoint='edit_community_resource')
class CommunityResourceEditView(DatasetView, NestedEditView):
    form = CommunityResourceForm
    nested_model = Resource
    nested_object_name = 'resource'
    nested_attribute = 'community_resources'
    template_name = 'dataset/resource/edit_community.html'

    def can(self, *args, **kwargs):
        permission = CommunityResourceEditPermission(self.nested_object)
        return permission.can()

    def get_success_url(self):
        return url_for('datasets.show', dataset=self.dataset)


@blueprint.route('/<dataset:dataset>/resources/<resource>/delete/', endpoint='delete_resource')
class ResourceDeleteView(ProtectedDatasetView, NestedObject, BaseView):
    nested_model = Resource
    nested_object_name = 'resource'
    nested_attribute = 'resources'

    def post(self, dataset, resource):
        dataset.resources.remove(self.nested_object)
        dataset.save()
        return redirect(url_for('datasets.show', dataset=self.dataset))


@blueprint.route('/<dataset:dataset>/community_resources/<resource>/delete/', endpoint='delete_community_resource')
class CommunityResourceDeleteView(ProtectedDatasetView, NestedObject, BaseView):
    nested_model = Resource
    nested_object_name = 'resource'
    nested_attribute = 'community_resources'

    def can(self, *args, **kwargs):
        permission = CommunityResourceEditPermission(self.nested_object)
        return permission.can()

    def post(self, dataset, resource):
        dataset.community_resources.remove(self.nested_object)
        dataset.save()
        return redirect(url_for('datasets.show', dataset=self.dataset))


@blueprint.route('/<dataset:dataset>/followers/', endpoint='followers')
class DatasetFollowersView(DatasetView, DetailView):
    template_name = 'dataset/followers.html'

    def get_context(self):
        context = super(DatasetFollowersView, self).get_context()
        context['followers'] = Follow.objects.followers(self.dataset).order_by('follower.fullname')
        return context
