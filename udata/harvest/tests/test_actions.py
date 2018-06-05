# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import logging
import pytest

from datetime import datetime
from tempfile import NamedTemporaryFile

from mock import patch

from udata.models import Dataset, PeriodicTask

from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.core.dataset.factories import DatasetFactory
from udata.tests.helpers import assert_emit
from udata.utils import faker, Paginable

from .factories import (
    HarvestSourceFactory, HarvestJobFactory, MockBackendsMixin,
    mock_initialize, mock_process, DEFAULT_COUNT as COUNT
)
from ..models import (
    HarvestSource, HarvestJob, HarvestError,
    VALIDATION_PENDING, VALIDATION_ACCEPTED, VALIDATION_REFUSED
)
from ..backends import BaseBackend
from .. import actions, signals


log = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.usefixtures('clean_db'),
]


class HarvestActionsTest:
    def test_list_backends(self):
        for backend in actions.list_backends():
            assert issubclass(backend, BaseBackend)

    def test_list_sources(self):
        assert actions.list_sources() == []

        sources = HarvestSourceFactory.create_batch(3)

        result = actions.list_sources()
        assert len(result) == len(sources)

        for source in sources:
            assert source in result

    def test_list_sources_deleted(self):
        assert actions.list_sources() == []

        now = datetime.now()
        sources = HarvestSourceFactory.create_batch(3)
        deleted_sources = HarvestSourceFactory.create_batch(2, deleted=now)

        result = actions.list_sources()
        assert len(result) == len(sources)

        for source in sources:
            assert source in result

        for source in deleted_sources:
            assert source not in result

    def test_list_sources_for_owner(self):
        owner = UserFactory()
        assert actions.list_sources(owner) == []

        sources = HarvestSourceFactory.create_batch(3, owner=owner)
        HarvestSourceFactory()

        result = actions.list_sources(owner)
        assert len(result) == len(sources)

        for source in sources:
            assert source in result

    def test_list_sources_for_org(self):
        org = OrganizationFactory()
        assert actions.list_sources(org) == []

        sources = HarvestSourceFactory.create_batch(3, organization=org)
        HarvestSourceFactory()

        result = actions.list_sources(org)
        assert len(result) == len(sources)

        for source in sources:
            assert source in result

    def test_paginate_sources(self):
        result = actions.paginate_sources()
        assert isinstance(result, Paginable)
        assert result.page == 1
        assert result.page_size == actions.DEFAULT_PAGE_SIZE
        assert result.total == 0
        assert len(result.objects) == 0

        HarvestSourceFactory.create_batch(3)

        result = actions.paginate_sources(page_size=2)
        assert isinstance(result, Paginable)
        assert result.page == 1
        assert result.page_size == 2
        assert result.total == 3
        assert len(result.objects) == 2

        result = actions.paginate_sources(page=2, page_size=2)
        assert isinstance(result, Paginable)
        assert result.page == 2
        assert result.page_size == 2
        assert result.total == 3
        assert len(result.objects) == 1

    def test_create_source(self):
        source_url = faker.url()

        with assert_emit(signals.harvest_source_created):
            source = actions.create_source('Test source',
                                           source_url,
                                           'factory')

        assert source.name == 'Test source'
        assert source.slug == 'test-source'
        assert source.url == source_url
        assert source.backend == 'factory'
        assert source.frequency == 'manual'
        assert source.active
        assert source.owner is None
        assert source.organization is None

        assert source.validation.state == VALIDATION_PENDING
        assert source.validation.on is None
        assert source.validation.by is None
        assert source.validation.comment is None

    def test_create_source_with_config(self):
        source_url = faker.url()
        config = {'filters': [{'key': 'test', 'value': 42}]}

        with assert_emit(signals.harvest_source_created):
            source = actions.create_source('Test source',
                                           source_url,
                                           'factory',
                                           config=config)

        assert source.config == config

    def test_update_source(self):
        source = HarvestSourceFactory()
        data = source.to_dict()
        new_url = faker.url()
        data['url'] = new_url

        with assert_emit(signals.harvest_source_updated):
            source = actions.update_source(source.id, data)

        assert source.url == new_url
        source.reload()
        assert source.url == new_url

    @patch('udata.harvest.actions.launch')
    def test_validate_source(self, mock):
        source = HarvestSourceFactory()

        actions.validate_source(source.id)

        source.reload()
        assert source.validation.state == VALIDATION_ACCEPTED
        assert source.validation.on is not None
        assert source.validation.by is None
        assert source.validation.comment is None
        mock.assert_called_once_with(source.id)

        assert source.periodic_task is not None

    @patch('udata.harvest.actions.launch')
    def test_validate_source_with_comment(self, mock):
        source = HarvestSourceFactory()

        actions.validate_source(source.id, 'comment')

        source.reload()

        assert source.validation.state == VALIDATION_ACCEPTED
        assert source.validation.on is not None
        assert source.validation.by is None
        assert source.validation.comment == 'comment'
        mock.assert_called_once_with(source.id)

    def test_reject_source(self):
        source = HarvestSourceFactory()

        actions.reject_source(source.id, 'comment')

        source.reload()
        assert source.validation.state == VALIDATION_REFUSED
        assert source.validation.on is not None
        assert source.validation.by is None
        assert source.validation.comment == 'comment'

    def test_get_source_by_slug(self):
        source = HarvestSourceFactory()
        assert actions.get_source(source.slug) == source

    def test_get_source_by_id(self):
        source = HarvestSourceFactory()
        assert actions.get_source(str(source.id)) == source

    def test_get_source_by_objectid(self):
        source = HarvestSourceFactory()
        assert actions.get_source(source.id) == source

    def test_delete_source_by_slug(self):
        source = HarvestSourceFactory()
        with assert_emit(signals.harvest_source_deleted):
            deleted_source = actions.delete_source(source.slug)

        assert deleted_source.deleted is not None
        assert deleted_source.id == source.id
        deleted_sources = HarvestSource.objects(deleted__exists=True)
        assert len(deleted_sources) == 1

    def test_delete_source_by_id(self):
        source = HarvestSourceFactory()
        with assert_emit(signals.harvest_source_deleted):
            deleted_source = actions.delete_source(str(source.id))

        assert deleted_source.deleted is not None
        assert deleted_source.id == source.id
        deleted_sources = HarvestSource.objects(deleted__exists=True)
        assert len(deleted_sources) == 1

    def test_delete_source_by_objectid(self):
        source = HarvestSourceFactory()
        with assert_emit(signals.harvest_source_deleted):
            deleted_source = actions.delete_source(source.id)

        assert deleted_source.deleted is not None
        assert deleted_source.id == source.id
        deleted_sources = HarvestSource.objects(deleted__exists=True)
        assert len(deleted_sources) == 1

    def test_get_job_by_id(self):
        job = HarvestJobFactory()
        assert actions.get_job(str(job.id)) == job

    def test_get_job_by_objectid(self):
        job = HarvestJobFactory()
        assert actions.get_job(job.id) == job

    def test_schedule(self):
        source = HarvestSourceFactory()
        with assert_emit(signals.harvest_source_scheduled):
            source = actions.schedule(str(source.id), hour=0)

        assert len(PeriodicTask.objects) == 1
        periodic_task = source.periodic_task
        assert periodic_task == PeriodicTask.objects.first()
        assert periodic_task.args == [str(source.id)]
        assert periodic_task.crontab.hour == '0'
        assert periodic_task.crontab.minute == '*'
        assert periodic_task.crontab.day_of_week == '*'
        assert periodic_task.crontab.day_of_month == '*'
        assert periodic_task.crontab.month_of_year == '*'
        assert periodic_task.enabled
        assert periodic_task.name == 'Harvest {0}'.format(source.name)

    def test_schedule_from_cron(self):
        source = HarvestSourceFactory()
        with assert_emit(signals.harvest_source_scheduled):
            source = actions.schedule(str(source.id), '0 1 2 3 sunday')

        assert len(PeriodicTask.objects) == 1
        periodic_task = source.periodic_task
        assert periodic_task == PeriodicTask.objects.first()
        assert periodic_task.args == [str(source.id)]
        assert periodic_task.crontab.minute == '0'
        assert periodic_task.crontab.hour == '1'
        assert periodic_task.crontab.day_of_month == '2'
        assert periodic_task.crontab.month_of_year == '3'
        assert periodic_task.crontab.day_of_week == 'sunday'
        assert periodic_task.enabled
        assert periodic_task.name == 'Harvest {0}'.format(source.name)

    def test_reschedule(self):
        source = HarvestSourceFactory()
        with assert_emit(signals.harvest_source_scheduled):
            source = actions.schedule(str(source.id), hour=0)

        with assert_emit(signals.harvest_source_scheduled):
            source = actions.schedule(str(source.id), minute=0)

        assert len(PeriodicTask.objects) == 1
        periodic_task = source.periodic_task
        assert periodic_task == PeriodicTask.objects.first()
        assert periodic_task.args == [str(source.id)]
        assert periodic_task.crontab.hour == '*'
        assert periodic_task.crontab.minute == '0'
        assert periodic_task.crontab.day_of_week == '*'
        assert periodic_task.crontab.day_of_month == '*'
        assert periodic_task.crontab.month_of_year == '*'
        assert periodic_task.enabled
        assert periodic_task.name == 'Harvest {0}'.format(source.name)

    def test_unschedule(self):
        periodic_task = PeriodicTask.objects.create(
            task='harvest',
            name=faker.name(),
            description=faker.sentence(),
            enabled=True,
            crontab=PeriodicTask.Crontab()
        )
        source = HarvestSourceFactory(periodic_task=periodic_task)
        with assert_emit(signals.harvest_source_unscheduled):
            actions.unschedule(str(source.id))

        source.reload()
        assert len(PeriodicTask.objects) == 0
        assert source.periodic_task is None

    def test_purge_sources(self):
        now = datetime.now()
        to_delete = HarvestSourceFactory.create_batch(3, deleted=now)
        to_keep = HarvestSourceFactory.create_batch(2)

        result = actions.purge_sources()

        assert result == len(to_delete)
        assert len(HarvestSource.objects) == len(to_keep)

    def test_attach(self):
        datasets = DatasetFactory.create_batch(3)

        with NamedTemporaryFile() as csvfile:
            writer = csv.DictWriter(csvfile,
                                    fieldnames=['local', 'remote'],
                                    delimiter=b';',
                                    quotechar=b'"')

            writer.writeheader()
            for index, dataset in enumerate(datasets):
                writer.writerow({
                    'local': str(dataset.id),
                    'remote': str(index)
                })
            csvfile.flush()

            result = actions.attach('test.org', csvfile.name)

        assert result.success == len(datasets)
        assert result.errors == 0
        for index, dataset in enumerate(datasets):
            dataset.reload()
            assert dataset.extras['harvest:domain'] == 'test.org'
            assert dataset.extras['harvest:remote_id'] == str(index)

    def test_attach_does_not_duplicate(self):
        attached_datasets = []
        for i in range(2):
            dataset = DatasetFactory.build()
            dataset.extras['harvest:domain'] = 'test.org'
            dataset.extras['harvest:remote_id'] = str(i)
            dataset.last_modified = datetime.now()
            dataset.save()
            attached_datasets.append(dataset)

        datasets = DatasetFactory.create_batch(3)

        with NamedTemporaryFile() as csvfile:
            writer = csv.DictWriter(csvfile,
                                    fieldnames=['local', 'remote'],
                                    delimiter=b';',
                                    quotechar=b'"')

            writer.writeheader()
            for index, dataset in enumerate(datasets):
                writer.writerow({
                    'local': str(dataset.id),
                    'remote': str(index)
                })
            csvfile.flush()

            result = actions.attach('test.org', csvfile.name)

        dbcount = Dataset.objects(**{
            'extras__harvest:remote_id__exists': True
        }).count()
        assert result.success == len(datasets)
        assert dbcount == result.success
        for index, dataset in enumerate(datasets):
            dataset.reload()
            assert dataset.extras['harvest:domain'] == 'test.org'
            assert dataset.extras['harvest:remote_id'] == str(index)

    def test_attach_skip_not_found(self):
        datasets = DatasetFactory.create_batch(3)

        with NamedTemporaryFile() as csvfile:
            writer = csv.DictWriter(csvfile,
                                    fieldnames=['local', 'remote'],
                                    delimiter=b';',
                                    quotechar=b'"')

            writer.writeheader()
            writer.writerow({
                'local': 'not-found',
                'remote': '42'
            })
            for index, dataset in enumerate(datasets):
                writer.writerow({
                    'local': str(dataset.id),
                    'remote': str(index)
                })
            csvfile.flush()

            result = actions.attach('test.org', csvfile.name)

        assert result.success == len(datasets)
        assert result.errors == 1


class ExecutionTestMixin(MockBackendsMixin):
    def test_default(self):
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='factory', organization=org)
        with assert_emit(signals.before_harvest_job,
                         signals.after_harvest_job):
            self.action(source.slug)

        source.reload()
        assert len(HarvestJob.objects(source=source)) == 1

        job = source.get_last_job()

        assert job.status == 'done'
        assert job.errors == []
        assert job.started is not None
        assert job.ended is not None
        assert len(job.items) == COUNT

        for item in job.items:
            assert item.status == 'done'
            assert item.errors == []
            assert item.started is not None
            assert item.ended is not None
            assert item.dataset is not None

            dataset = item.dataset
            assert Dataset.objects(id=dataset.id).first() is not None
            assert dataset.organization == org
            assert 'harvest:remote_id' in dataset.extras
            assert 'harvest:last_update' in dataset.extras
            assert 'harvest:source_id' in dataset.extras

        assert len(HarvestJob.objects) == 1
        assert len(Dataset.objects) == COUNT

    def test_error_on_initialize(self):
        def init(self):
            raise ValueError('test')

        source = HarvestSourceFactory(backend='factory')
        with assert_emit(signals.before_harvest_job),\
                mock_initialize.connected_to(init):
            self.action(source.slug)

        source.reload()
        assert len(HarvestJob.objects(source=source)) == 1

        job = source.get_last_job()
        assert job.status == 'failed'
        assert len(job.errors) == 1
        error = job.errors[0]
        assert isinstance(error, HarvestError)
        assert job.started is not None
        assert job.ended is not None
        assert len(job.items) == 0

        assert len(HarvestJob.objects) == 1
        assert len(Dataset.objects) == 0

    def test_error_on_item(self):
        def process(self, item):
            if item.remote_id == '1':
                raise ValueError('test')

        source = HarvestSourceFactory(backend='factory')
        with assert_emit(signals.before_harvest_job,
                         signals.after_harvest_job), \
                mock_process.connected_to(process):
            self.action(source.slug)

        source.reload()
        assert len(HarvestJob.objects(source=source)) == 1

        job = source.get_last_job()
        assert job.status == 'done-errors'
        assert job.started is not None
        assert job.ended is not None
        assert len(job.errors) == 0
        assert len(job.items) == COUNT

        items_ok = filter(lambda i: not len(i.errors), job.items)
        assert len(items_ok) == COUNT - 1

        for item in items_ok:
            assert item.started is not None
            assert item.ended is not None
            assert item.status == 'done'
            assert item.errors == []

        item_ko = filter(lambda i: len(i.errors), job.items)[0]
        assert item_ko.started is not None
        assert item_ko.ended is not None
        assert item_ko.status == 'failed'
        assert len(item_ko.errors) == 1

        error = item_ko.errors[0]
        assert isinstance(error, HarvestError)

        assert len(HarvestJob.objects) == 1
        assert len(Dataset.objects) == COUNT - 1

    def test_empty(self):
        source = HarvestSourceFactory(backend='factory', config={'count': 0})
        with assert_emit(signals.before_harvest_job,
                         signals.after_harvest_job):
            self.action(source.slug)

        source.reload()
        assert len(HarvestJob.objects(source=source)) == 1

        job = source.get_last_job()

        assert job.status == 'done'
        assert job.errors == []
        assert job.started is not None
        assert job.ended is not None
        assert job.items == []

        assert len(HarvestJob.objects) == 1
        assert len(Dataset.objects) == 0


class HarvestLaunchTest(ExecutionTestMixin):
    def action(self, *args, **kwargs):
        return actions.launch(*args, **kwargs)


class HarvestRunTest(ExecutionTestMixin):
    def action(self, *args, **kwargs):
        return actions.run(*args, **kwargs)


class HarvestPreviewTest(MockBackendsMixin):
    def test_preview(self):
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='factory', organization=org)

        job = actions.preview(source.slug)

        assert job.status == 'done'
        assert job.errors == []
        assert job.started is not None
        assert job.ended is not None
        assert len(job.items) == COUNT

        for item in job.items:
            assert item.status == 'done'
            assert item.errors == []
            assert item.started is not None
            assert item.ended is not None
            assert item.dataset is not None

            dataset = item.dataset
            assert dataset.organization == org
            assert 'harvest:remote_id' in dataset.extras
            assert 'harvest:last_update' in dataset.extras
            assert 'harvest:source_id' in dataset.extras

        assert len(HarvestJob.objects) == 0
        assert len(Dataset.objects) == 0

    @pytest.mark.options(HARVEST_PREVIEW_MAX_ITEMS=5)
    def test_preview_max_items(self):
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='factory',
                                      organization=org,
                                      config={'count': 10})

        job = actions.preview(source.slug)

        assert len(job.items) == 5

    def test_preview_with_error_on_initialize(self):
        def init(self):
            raise ValueError('test')

        source = HarvestSourceFactory(backend='factory')

        with mock_initialize.connected_to(init):
            job = actions.preview(source.slug)

        assert job.status == 'failed'
        assert len(job.errors) == 1
        error = job.errors[0]
        assert isinstance(error, HarvestError)
        assert job.started is not None
        assert job.ended is not None
        assert len(job.items) == 0

        assert len(HarvestJob.objects) == 0
        assert len(Dataset.objects) == 0

    def test_preview_with_error_on_item(self):
        def process(self, item):
            if item.remote_id == '1':
                raise ValueError('test')

        source = HarvestSourceFactory(backend='factory')

        with mock_process.connected_to(process):
            job = actions.preview(source.slug)

        assert job.status == 'done-errors'
        assert job.started is not None
        assert job.ended is not None
        assert len(job.errors) == 0
        assert len(job.items) == COUNT

        items_ok = filter(lambda i: not len(i.errors), job.items)
        assert len(items_ok) == COUNT - 1

        for item in items_ok:
            assert item.started is not None
            assert item.ended is not None
            assert item.status == 'done'
            assert item.errors == []

        item_ko = filter(lambda i: len(i.errors), job.items)[0]
        assert item_ko.started is not None
        assert item_ko.ended is not None
        assert item_ko.status == 'failed'
        assert len(item_ko.errors) == 1

        error = item_ko.errors[0]
        assert isinstance(error, HarvestError)

        assert len(HarvestJob.objects) == 0
        assert len(Dataset.objects) == 0
