# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import abort, request, url_for, render_template
from werkzeug.contrib.atom import AtomFeed

from udata.frontend.views import DetailView, SearchView
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.models import Dataset, Discussion, Follow, Reuse
from udata.core.organization.views import OrganizationDetailView
from udata.core.site.views import current_site
from udata.core.user.views import UserActivityView
from udata.sitemap import sitemap

from .permissions import ResourceEditPermission, DatasetEditPermission

blueprint = I18nBlueprint('datasets', __name__, url_prefix='/datasets')


@blueprint.route('/recent.atom')
def recent_feed():
    feed = AtomFeed(_('Last datasets'),
                    feed_url=request.url, url=request.url_root)
    datasets = (Dataset.objects.visible().order_by('-created_at')
                .limit(current_site.feed_size))
    for dataset in datasets:
        author = None
        if dataset.organization:
            author = {
                'name': dataset.organization.name,
                'uri': url_for('organizations.show',
                               org=dataset.organization.id, _external=True),
            }
        elif dataset.owner:
            author = {
                'name': dataset.owner.fullname,
                'uri': url_for('users.show',
                               user=dataset.owner.id, _external=True),
            }
        feed.add(dataset.title,
                 render_template('dataset/feed_item.html', dataset=dataset),
                 content_type='html',
                 author=author,
                 url=url_for('datasets.show',
                             dataset=dataset.id, _external=True),
                 updated=dataset.last_modified,
                 published=dataset.created_at)
    return feed.get_response()


@blueprint.route('/', endpoint='list')
class DatasetListView(SearchView):
    model = Dataset
    context_name = 'datasets'
    template_name = 'dataset/list.html'


class DatasetView(object):
    model = Dataset
    object_name = 'dataset'

    @property
    def dataset(self):
        return self.get_object()

    def get_context(self):
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
        if not DatasetEditPermission(self.dataset).can():
            if self.dataset.private:
                abort(404)
            elif self.dataset.deleted:
                abort(410)
        context['reuses'] = Reuse.objects(datasets=self.dataset).visible()
        context['can_edit'] = DatasetEditPermission(self.dataset)
        context['can_edit_resource'] = ResourceEditPermission
        context['discussions'] = Discussion.objects(subject=self.dataset)

        return context

    def get_json_ld(self):
        dataset = self.dataset

        result = {
            '@context': 'http://schema.org',
            '@type': 'Dataset',
            '@id': str(dataset.id),
            'description': dataset.description,
            'alternateName': dataset.slug,
            'dateCreated': dataset.created_at.isoformat(),
            'dateModified': dataset.last_modified.isoformat(),
            'url': url_for('datasets.show', dataset=dataset, _external=True),
            'name': dataset.title,
            'keywords': ', '.join(dataset.tags),
            'distribution': map(self.get_json_ld_resource, dataset.resources),
            # This value is not standard
            'extras': map(self.get_json_ld_extra, dataset.extras.items()),
        }

        if dataset.license and dataset.license.url:
            result['license'] = dataset.license.url

        if dataset.organization:
            view = OrganizationDetailView()
            author = view.get_json_ld(dataset.organization)
        elif dataset.owner:
            view = UserActivityView()
            author = view.get_json_ld(dataset.owner)
        else:
            author = None

        if author:
            result['author'] = author

        return result

    @staticmethod
    def get_json_ld_resource(resource):

        result = {
            '@type': 'DataDownload',
            '@id': str(resource.id),
            'url': resource.url,
            'name': resource.title or _('Nameless resource'),
            'contentUrl': resource.url,
            'encodingFormat': resource.format or '',
            'dateCreated': resource.created_at.isoformat(),
            'dateModified': resource.modified.isoformat(),
            'datePublished': resource.published.isoformat(),
            'contentSize': resource.filesize or '',
            'fileFormat': resource.mime or '',
            'interactionStatistic': {
                '@type': 'InteractionCounter',
                'interactionType': {
                    '@type': 'DownloadAction',
                },
                # We take resource.metrics.views if it exists
                'userInteractionCount': getattr(resource.metrics, 'views', ''),
            },
        }

        if resource.description:
            result['description'] = resource.description

        # These 2 values are not standard
        if resource.checksum:
            result['checksum'] = resource.checksum.value,
            result['checksumType'] = resource.checksum.type or 'sha1'

        return result

    @staticmethod
    def get_json_ld_extra(key, value):
        return {
            '@type': 'http://schema.org/PropertyValue',
            'name': key,
            'value': value.serialize() if value.serialize else value,
        }


@blueprint.route('/<dataset:dataset>/followers/', endpoint='followers')
class DatasetFollowersView(DatasetView, DetailView):
    template_name = 'dataset/followers.html'

    def get_context(self):
        context = super(DatasetFollowersView, self).get_context()
        context['followers'] = (Follow.objects.followers(self.dataset)
                                              .order_by('follower.fullname'))
        return context


@sitemap.register_generator
def sitemap_urls():
    for dataset in Dataset.objects.visible().only('id', 'slug'):
        yield ('datasets.show_redirect', {'dataset': dataset},
               None, 'weekly', 0.8)
