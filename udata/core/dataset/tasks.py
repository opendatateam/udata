# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from compiler.ast import flatten
from datetime import datetime, timedelta
from sets import Set
from tempfile import NamedTemporaryFile

from celery.utils.log import get_task_logger
from flask import current_app

from udata import mail
from udata import models as udata_models
from udata.core import storages
from udata.frontend import csv
from udata.i18n import lazy_gettext as _
from udata.models import (Follow, Issue, Discussion, Activity, Metrics, Topic,
                          Organization)
from udata.tasks import job

from .models import Dataset, Resource, UPDATE_FREQUENCIES, Checksum

log = get_task_logger(__name__)


@job('purge-datasets')
def purge_datasets(self):
    for dataset in Dataset.objects(deleted__ne=None):
        log.info('Purging dataset "{0}"'.format(dataset))
        # Remove followers
        Follow.objects(following=dataset).delete()
        # Remove issues
        Issue.objects(subject=dataset).delete()
        # Remove discussions
        Discussion.objects(subject=dataset).delete()
        # Remove activity
        Activity.objects(related_to=dataset).delete()
        # Remove metrics
        Metrics.objects(object_id=dataset.id).delete()
        # Remove topics' related dataset
        for topic in Topic.objects(datasets=dataset):
            datasets = topic.datasets
            datasets.remove(dataset)
            topic.update(datasets=datasets)
        # Remove
        dataset.delete()


@job('send-frequency-reminder')
def send_frequency_reminder(self):
    # We exclude irrelevant frequencies.
    frequencies = [f for f in UPDATE_FREQUENCIES.keys()
                   if f not in ('unknown', 'realtime', 'punctual')]
    now = datetime.now()
    reminded_orgs = {}
    reminded_people = []
    allowed_delay = current_app.config['DELAY_BEFORE_REMINDER_NOTIFICATION']
    for org in Organization.objects.visible():
        outdated_datasets = []
        for dataset in Dataset.objects.filter(
                frequency__in=frequencies, organization=org).visible():
            if dataset.next_update + timedelta(days=allowed_delay) < now:
                dataset.outdated = now - dataset.next_update
                dataset.frequency_str = UPDATE_FREQUENCIES[dataset.frequency]
                outdated_datasets.append(dataset)
        if outdated_datasets:
            reminded_orgs[org] = outdated_datasets
    for reminded_org, datasets in reminded_orgs.iteritems():
        print('{org.name} will be emailed for {datasets_nb} datasets'.format(
              org=reminded_org, datasets_nb=len(datasets)))
        recipients = [m.user for m in reminded_org.members]
        reminded_people.append(recipients)
        subject = _('You need to update some frequency-based datasets')
        mail.send(subject, recipients, 'frequency_reminder',
                  org=reminded_org, datasets=datasets)

    print('{nb_orgs} orgs concerned'.format(nb_orgs=len(reminded_orgs)))
    reminded_people = flatten(reminded_people)
    print('{nb_emails} people contacted ({nb_emails_twice} twice)'.format(
        nb_emails=len(reminded_people),
        nb_emails_twice=len(reminded_people) - len(Set(reminded_people))))
    print('Done')


def get_queryset(model_cls):
    # special case for resources
    if model_cls.__name__ == 'Resource':
        model_cls = getattr(udata_models, 'Dataset')
    params = {}
    attrs = ('private', 'deleted')
    for attr in attrs:
        if getattr(model_cls, attr, None):
            params[attr] = False
    return model_cls.objects.filter(**params)


def get_or_create_resource(r_info, model, dataset):
    resource = None
    for r in dataset.resources:
        if r.extras.get('csv-export:model', '') == model:
            resource = r
            break
    if resource:
        for k, v in r_info.items():
            setattr(resource, k, v)
        resource.save()
        return False, resource
    else:
        r_info['extras'] = {'csv-export:model': model}
        return True, Resource(**r_info)


def store_resource(csvfile, model, dataset):
    timestr = datetime.now().strftime('%Y%m%d-%H%M%S')
    filename = 'export-%s-%s.csv' % (model, timestr)
    prefix = '/'.join((dataset.slug, timestr))
    storage = storages.resources
    stored_filename = storage.save(csvfile, prefix=prefix, filename=filename)
    r_info = storage.metadata(stored_filename)
    checksum = r_info.pop('checksum')
    algo, checksum = checksum.split(':', 1)
    r_info[algo] = checksum
    r_info['format'] = storages.utils.extension(stored_filename)
    r_info['checksum'] = Checksum(type='sha1', value=r_info.pop('sha1'))
    r_info['filesize'] = r_info.pop('size')
    del r_info['filename']
    r_info['title'] = filename
    return get_or_create_resource(r_info, model, dataset)


def export_csv_for_model(model, dataset):
    model_cls = getattr(udata_models, model.capitalize(), None)
    if not model_cls:
        log.error('Unknow model %s' % model)
        return
    queryset = get_queryset(model_cls)
    adapter = csv.get_adapter(model_cls)
    if not adapter:
        log.error('No adapter found for %s' % model)
        return
    adapter = adapter(queryset)

    log.info('Exporting CSV for %s...' % model)

    csvfile = NamedTemporaryFile(delete=False)
    try:
        # write adapter results into a tmp file
        writer = csv.get_writer(csvfile)
        writer.writerow(adapter.header())
        for row in adapter.rows():
            writer.writerow(row)
        csvfile.seek(0)
        # make a resource from this tmp file
        created, resource = store_resource(csvfile, model, dataset)
        # add it to the dataset
        if created:
            dataset.add_resource(resource)
        dataset.last_modified = datetime.now()
        dataset.save()
    finally:
        os.unlink(csvfile.name)


@job('export-csv')
def export_csv(self):
    '''
    Generates a CSV export of all model objects as a resource of a dataset
    '''
    ALLOWED_MODELS = current_app.config.get('EXPORT_CSV_MODELS', [])
    DATASET_DEFAULTS = current_app.config.get('EXPORT_CSV_DATASET_INFO')

    if ALLOWED_MODELS:
        slug = DATASET_DEFAULTS.pop('slug')
        organization = DATASET_DEFAULTS.get('organization')
        if organization:
            try:
                DATASET_DEFAULTS['organization'] = Organization.objects.get(id=organization)
            except Organization.DoesNotExist:
                log.error('Organization with id %s not found.' % organization)
        dataset, _ = Dataset.objects.get_or_create(
            slug=slug,
            defaults=DATASET_DEFAULTS,
        )

    for model in ALLOWED_MODELS:
        export_csv_for_model(model, dataset)
