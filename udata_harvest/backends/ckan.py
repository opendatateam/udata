# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from uuid import UUID
from urlparse import urljoin

import requests

from flask.ext.security import current_user

from udata.models import db, Dataset, Resource, Organization, Reuse, User, License, TerritorialCoverage, Member
from udata.models import Follow, FollowOrg, FollowDataset
from udata.utils import get_by, daterange_start, daterange_end

from . import BaseBackend


log = logging.getLogger(__name__)


def any_field(data, *args):
    return any(map(lambda f: data.get(f), args))


def all_field(data, *args):
    return all(map(lambda f: data.get(f), args))


class CkanBackend(BaseBackend):
    name = 'ckan'
    page_size = 20

    def initialize(self):
        self.headers = {
            'content-type': 'application/json',
        }
        if self.config.get('apikey'):
            self.headers['Authorization'] = self.harvester.config['apikey']

    def url(self, endpoint):
        path = '/'.join(['api/3/action', endpoint])
        return urljoin(self.harvester.config['url'], path)

    def get(self, url, params=None):
        return requests.get(self.url(url), params=params or {}, headers=self.headers).json()

    def post(self, url, payload=None, params=None):
        return requests.post(self.url(url), payload=payload, params=params or {}, headers=self.headers).json()

    def remote_users(self):
        if self.config.get('users') is None:
            return
        response = self.get('user_list')
        for data in response['result']:
            # if self.config['users'].get('match_by_email'):
            if not data.get('email'):
                continue
            user = self.get_harvested(User, data['id'])
            user.email = data['email']
            user.slug = data['name']
            name = data['display_name']
            user.first_name = name.split(' ', 1)[0] if ' ' in name else name
            user.last_name = name.split(' ', 1)[1] if ' ' in name else name
            user.about = data['about']

            yield user

            # followers = self.get('user_follower_list', {'id': name})['result']
            # for follower in followers:
            #     user_follower = self.get_harvested(User, follower['id'])
            #     follow, created = FollowDataset.objects.get_or_create(follower=user_follower, following=user)

            # {
            #     "openid": null,
            #     "about": null,
            #     "apikey": "9c1772bd-8b61-44cb-b749-2ae24b8ae63b",
            #     "display_name": "Aaron Micallef",
            #     "name": "aaron-micallef",
            #     "created": "2014-01-11T19:07:11.780066",
            #     "reset_key": null,
            #     "email": "micallefaaron@gmail.com",
            #     "sysadmin": false,
            #     "activity_streams_email_notifications": false,
            #     "email_hash": "75afe777d01ad7f5b8360b095dee33e7",
            #     "number_of_edits": 0,
            #     "number_administered_packages": 0,
            #     "fullname": "Aaron Micallef",
            #     "id": "4ed271c4-4d6e-4b5f-85c6-741739d55928"
            # }

    def remote_organizations(self):
        response = self.get('organization_list')
        for name in response['result']:
            details = self.get('organization_show', {'id': name})['result']
            organization = self.get_harvested(Organization, details['id'])
            organization.name = details['title']
            organization.slug = details['name']
            organization.description = details['description']
            organization.image_url = details['image_url'] or None

            if self.config.get('users') is not None:
                for member in details['users']:
                    user = self.get_harvested(User, member['id'], create=False)
                    if user and not get_by(organization.members, 'user', user):
                        role = 'admin' if member['capacity'] == 'admin' else 'editor'
                        organization.members.append(Member(role=role, user=user))

            yield organization

            if not organization.id:
                continue

            followers = self.get('group_follower_list', {'id': name})['result']
            for follower in followers:
                user = self.get_harvested(User, follower['id'], create=False)
                if user:
                    follow, created = FollowOrg.objects.get_or_create(follower=user, following=organization)

    def remote_datasets(self):
        response = self.get('package_list')
        for name in response['result']:
            details = self.get('package_show', {'id': name})['result']
            dataset = self.get_harvested(Dataset, details['id'])

            # Core attributes
            dataset.title = details['title']
            dataset.description = details.get('notes', 'No description')
            dataset.license = License.objects(id=details['license_id']).first() or License.objects.get(id='notspecified')
            dataset.tags = [tag['name'].lower() for tag in details['tags']]

            dataset.frequency = self.map('frequency', details)

            if any_field(details, 'territorial_coverage', 'territorial_coverage_granularity'):
                dataset.territorial_coverage = TerritorialCoverage(
                    codes=[code.strip() for code in details.get('territorial_coverage', '').split(',') if code.strip()],
                    granularity=self.map('territorial_coverage_granularity', details),
                )

            if all_field(details, 'temporal_coverage_from', 'temporal_coverage_to'):
                try:
                    dataset.temporal_coverage = db.DateRange(
                        start=daterange_start(details.get('temporal_coverage_from')),
                        end=daterange_end(details.get('temporal_coverage_to')),
                    )
                except:
                    log.error('Unable to parse temporal coverage for dataset %s', details['id'])

            # Organization
            if details.get('organization'):
                dataset.organization = self.get_harvested(Organization, details['organization']['id'], False)

            # Supplier
            if details.get('supplier_id'):
                dataset.supplier = self.get_harvested(Organization, details['supplier_id'], False)
                if dataset.supplier == dataset.organization:
                    dataset.supplier = None

            # Extras
            if 'extras' in details:
                extra_mapping = self.harvester.mapping.get('from_extras', {})
                for extra in details['extras']:
                    if extra['key'] in self.harvester.mapping:
                        value = self.harvester.mapping[extra['key']].get(extra['value'])
                    else:
                        value = extra['value']
                    if extra['key'] in extra_mapping:
                        setattr(dataset, extra_mapping[extra['key']], value)
                    else:
                        dataset.extras[extra['key']] = value

            # Resources
            for res in details['resources']:
                try:
                    resource = get_by(dataset.resources, 'id', UUID(res['id']))
                except:
                    log.error('Unable to parse resource %s', res['id'])
                    continue
                if not resource:
                    resource = Resource(id=res['id'])
                    dataset.resources.append(resource)
                resource.title = res.get('title', 'No name')
                resource.url = res['url']
                resource.description = res.get('description')
                resource.format = res.get('format')
                resource.hash = res.get('hash')
            yield dataset

            if dataset.id:
                followers = self.get('dataset_follower_list', {'id': name})['result']
                for follower in followers:
                    user = self.get_harvested(User, follower['id'], False)
                    if user:
                        follow, created = FollowDataset.objects.get_or_create(follower=user, following=dataset)

    def remote_reuses(self):
        # dataset_ids = (d.ext['harvest'].remote_id for d in Dataset.objects(ext__harvest__harvester=self.harvester.id))
        # response = self.get('package_list')
        # for dataset_id in response['result']:
        for dataset in Dataset.objects(ext__harvest__harvester=self.harvester.id).timeout(False):
            try:
                resp = self.get('related_list', {'id': dataset.ext['harvest'].remote_id})
            except:
                log.error('Unable to parse reuse for dataset %s', dataset.id)
                continue
            for details in resp['result']:
                reuse_url = details['url']
                reuse = self.get_harvested(Reuse, details['id'], url=reuse_url)
                reuse.title = details['title']
                reuse.description = details['description']
                reuse.type = details['type']
                reuse.url = details['url']
                reuse.image_url = details.get('image_url')
                if details.get('owner_id'):
                    reuse.owner = self.get_harvested(User, details['owner_id'])
                if not dataset in reuse.datasets:
                    reuse.datasets.append(dataset)
                    for tag in dataset.tags:
                        if not tag in reuse.tags:
                            reuse.tags.append(tag)
                yield reuse
