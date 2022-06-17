from io import StringIO

import pytest
from datetime import datetime

from flask import url_for

from udata.frontend import csv
from udata.models import Site

from udata.core.dataset import tasks as dataset_tasks
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.site.models import current_site
from udata.core.reuse.factories import ReuseFactory
from udata.harvest.models import HarvestSource
from udata_front.tests import GouvFrSettings
from udata_front.tests.frontend import GouvfrFrontTestCase


class SiteViewsTest(GouvfrFrontTestCase):
    settings = GouvFrSettings
    modules = ['admin']

    def test_site_global(self):
        '''It should create and/or load the current site'''
        with self.app.test_request_context(''):
            self.app.preprocess_request()
            self.assertIsInstance(current_site._get_current_object(), Site)
            self.assertEqual(current_site.id, self.app.config['SITE_ID'])

    def test_render_home(self):
        '''It should render the home page'''
        for i in range(3):
            org = OrganizationFactory()
            DatasetFactory(organization=org)
            ReuseFactory(organization=org)

        current_site.settings.home_datasets = [
            DatasetFactory() for _ in range(3)]
        current_site.settings.home_reuses = [
            ReuseFactory() for _ in range(3)]

        response = self.get(url_for('site.home'))
        self.assert200(response)

    def test_render_home_no_data(self):
        '''It should render the home page without data'''
        response = self.get(url_for('site.home'))
        self.assert200(response)

    @pytest.mark.options(BANNER_ACTIVATED=False)
    @pytest.mark.options(BANNER_HTML_CONTENT_EN='BANNER_TEST')
    def test_render_home_no_banner(self):
        '''It should render the home page without banner'''
        response = self.get(url_for('site.home'))
        self.assert200(response)
        self.assertNotIn(b"BANNER_TEST", response.data)

    @pytest.mark.options(BANNER_ACTIVATED=True)
    @pytest.mark.options(BANNER_HTML_CONTENT_EN='BANNER_TEST_EN')
    @pytest.mark.options(BANNER_HTML_CONTENT_FR='BANNER_TEST_FR')
    def test_render_home_with_banner(self):
        '''It should render the home page with a banner'''
        response = self.get(url_for('site.home', lang_code='en'))
        self.assert200(response)
        self.assertIn(b"BANNER_TEST_EN", response.data)

        response = self.get(url_for('site.home', lang_code='fr'))
        self.assert200(response)
        self.assertIn(b"BANNER_TEST_FR", response.data)

    def test_render_dashboard(self):
        '''It should render the search page'''
        for i in range(3):
            org = OrganizationFactory()
            DatasetFactory(organization=org)
            ReuseFactory(organization=org)
        response = self.get(url_for('site.dashboard'))
        self.assert200(response)

    def test_render_dashboard_no_data(self):
        '''It should render the search page without data'''
        response = self.get(url_for('site.dashboard'))
        self.assert200(response)

    def test_datasets_csv(self):
        self.app.config['EXPORT_CSV_MODELS'] = []
        datasets = [DatasetFactory(resources=[ResourceFactory()])
                    for _ in range(5)]
        hidden_dataset = DatasetFactory()

        response = self.get(url_for('site.datasets_csv'))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO(response.data.decode('utf8'))
        reader = csv.get_reader(csvfile)
        header = next(reader)

        self.assertEqual(header[0], 'id')
        self.assertIn('title', header)
        self.assertIn('description', header)
        self.assertIn('created_at', header)
        self.assertIn('last_modified', header)
        self.assertIn('tags', header)
        self.assertIn('metric.reuses', header)

        rows = list(reader)
        ids = [row[0] for row in rows]

        self.assertEqual(len(rows), len(datasets))
        for dataset in datasets:
            self.assertIn(str(dataset.id), ids)
        self.assertNotIn(str(hidden_dataset.id), ids)

    @pytest.mark.usefixtures('instance_path')
    def test_datasets_csv_w_export_csv_feature(self):
        # no export generated, 404
        response = self.get(url_for('site.datasets_csv'))
        self.assert404(response)

        # generate the export
        d = DatasetFactory()
        self.app.config['EXPORT_CSV_DATASET_ID'] = d.id
        dataset_tasks.export_csv()
        response = self.get(url_for('site.datasets_csv'))
        self.assertStatus(response, 302)
        self.assertIn('export-dataset-', response.location)

    def test_datasets_csv_with_filters(self):
        '''Should handle filtering but ignore paging'''
        filtered_datasets = [
            DatasetFactory(resources=[ResourceFactory()],
                           tags=['selected'])
            for _ in range(6)]
        datasets = [DatasetFactory(resources=[ResourceFactory()])
                    for _ in range(3)]
        hidden_dataset = DatasetFactory()

        response = self.get(
            url_for(
                'site.datasets_csv', tag='selected', page_size=3))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO(response.data.decode('utf8'))
        reader = csv.get_reader(csvfile)
        header = next(reader)

        self.assertEqual(header[0], 'id')
        self.assertIn('title', header)
        self.assertIn('description', header)
        self.assertIn('created_at', header)
        self.assertIn('last_modified', header)
        self.assertIn('tags', header)
        self.assertIn('metric.reuses', header)

        rows = list(reader)
        ids = [row[0] for row in rows]

        # Should ignore paging
        self.assertEqual(len(rows), len(filtered_datasets))
        # SHoulf pass filter
        for dataset in filtered_datasets:
            self.assertIn(str(dataset.id), ids)
        for dataset in datasets:
            self.assertNotIn(str(dataset.id), ids)
        self.assertNotIn(str(hidden_dataset.id), ids)

    def test_resources_csv(self):
        self.app.config['EXPORT_CSV_MODELS'] = []
        datasets = [
         DatasetFactory(resources=[ResourceFactory(),
                                   ResourceFactory()])
         for _ in range(3)]
        DatasetFactory()

        response = self.get(url_for('site.resources_csv'))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO(response.data.decode('utf8'))
        reader = csv.get_reader(csvfile)
        header = next(reader)

        self.assertEqual(header[0], 'dataset.id')
        self.assertIn('dataset.title', header)
        self.assertIn('dataset.url', header)
        self.assertIn('title', header)
        self.assertIn('description', header)
        self.assertIn('filetype', header)
        self.assertIn('url', header)
        self.assertIn('created_at', header)
        self.assertIn('modified', header)
        self.assertIn('downloads', header)

        resource_id_index = header.index('id')

        rows = list(reader)
        ids = [(row[0], row[resource_id_index]) for row in rows]

        self.assertEqual(len(rows), sum(len(d.resources) for d in datasets))
        for dataset in datasets:
            for resource in dataset.resources:
                self.assertIn((str(dataset.id), str(resource.id)), ids)

    @pytest.mark.usefixtures('instance_path')
    def test_resources_csv_w_export_csv_feature(self):
        # no export generated, 404
        response = self.get(url_for('site.resources_csv'))
        self.assert404(response)

        # generate the export
        d = DatasetFactory()
        self.app.config['EXPORT_CSV_DATASET_ID'] = d.id
        dataset_tasks.export_csv()
        response = self.get(url_for('site.resources_csv'))
        self.assertStatus(response, 302)
        self.assertIn('export-resource-', response.location)

    def test_resources_csv_with_filters(self):
        '''Should handle filtering but ignore paging'''
        filtered_datasets = [DatasetFactory(resources=[ResourceFactory(),
                             ResourceFactory()],
                             tags=['selected'])
                             for _ in range(6)]
        [DatasetFactory(resources=[ResourceFactory()]) for _ in range(3)]
        DatasetFactory()

        response = self.get(
            url_for('site.resources_csv', tag='selected', page_size=3))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO(response.data.decode('utf8'))
        reader = csv.get_reader(csvfile)
        header = next(reader)

        self.assertEqual(header[0], 'dataset.id')
        self.assertIn('dataset.title', header)
        self.assertIn('dataset.url', header)
        self.assertIn('title', header)
        self.assertIn('description', header)
        self.assertIn('filetype', header)
        self.assertIn('url', header)
        self.assertIn('created_at', header)
        self.assertIn('modified', header)
        self.assertIn('downloads', header)

        resource_id_index = header.index('id')

        rows = list(reader)
        ids = [(row[0], row[resource_id_index]) for row in rows]

        self.assertEqual(len(rows),
                         sum(len(d.resources) for d in filtered_datasets))
        for dataset in filtered_datasets:
            for resource in dataset.resources:
                self.assertIn((str(dataset.id), str(resource.id)), ids)

    def test_organizations_csv(self):
        self.app.config['EXPORT_CSV_MODELS'] = []
        orgs = [OrganizationFactory() for _ in range(5)]
        hidden_org = OrganizationFactory(deleted=datetime.now())

        response = self.get(url_for('site.organizations_csv'))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO(response.data.decode('utf8'))
        reader = csv.get_reader(csvfile)
        header = next(reader)

        self.assertEqual(header[0], 'id')
        self.assertIn('name', header)
        self.assertIn('description', header)
        self.assertIn('created_at', header)
        self.assertIn('last_modified', header)
        self.assertIn('metric.datasets', header)

        rows = list(reader)
        ids = [row[0] for row in rows]

        self.assertEqual(len(rows), len(orgs))
        for org in orgs:
            self.assertIn(str(org.id), ids)
        self.assertNotIn(str(hidden_org.id), ids)

    @pytest.mark.usefixtures('instance_path')
    def test_organizations_csv_w_export_csv_feature(self):
        # no export generated, 404
        response = self.get(url_for('site.organizations_csv'))
        self.assert404(response)

        # generate the export
        d = DatasetFactory()
        self.app.config['EXPORT_CSV_DATASET_ID'] = d.id
        dataset_tasks.export_csv()
        response = self.get(url_for('site.organizations_csv'))
        self.assertStatus(response, 302)
        self.assertIn('export-organization-', response.location)

    def test_reuses_csv(self):
        self.app.config['EXPORT_CSV_MODELS'] = []
        reuses = [ReuseFactory(datasets=[DatasetFactory()])
                  for _ in range(5)]
        hidden_reuse = ReuseFactory()

        response = self.get(url_for('site.reuses_csv'))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO(response.data.decode('utf8'))
        reader = csv.get_reader(csvfile)
        header = next(reader)

        self.assertEqual(header[0], 'id')
        self.assertIn('title', header)
        self.assertIn('description', header)
        self.assertIn('created_at', header)
        self.assertIn('last_modified', header)
        self.assertIn('tags', header)
        self.assertIn('metric.datasets', header)

        rows = list(reader)
        ids = [row[0] for row in rows]

        self.assertEqual(len(rows), len(reuses))
        for reuse in reuses:
            self.assertIn(str(reuse.id), ids)
        self.assertNotIn(str(hidden_reuse.id), ids)

    @pytest.mark.usefixtures('instance_path')
    def test_reuses_csv_w_export_csv_feature(self):
        # no export generated, 404
        response = self.get(url_for('site.reuses_csv'))
        self.assert404(response)

        # generate the export
        d = DatasetFactory()
        self.app.config['EXPORT_CSV_DATASET_ID'] = d.id
        dataset_tasks.export_csv()
        response = self.get(url_for('site.reuses_csv'))
        self.assertStatus(response, 302)
        self.assertIn('export-reuse-', response.location)

    def test_reuses_csv_with_filters(self):
        '''Should handle filtering but ignore paging or facets'''
        filtered_reuses = [
            ReuseFactory(datasets=[DatasetFactory()], tags=['selected'])
            for _ in range(6)]
        reuses = [ReuseFactory(datasets=[DatasetFactory()])
                  for _ in range(3)]
        hidden_reuse = ReuseFactory()

        response = self.get(
            url_for('site.reuses_csv', tag='selected', page_size=3))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO(response.data.decode('utf8'))
        reader = csv.get_reader(csvfile)
        header = next(reader)

        self.assertEqual(header[0], 'id')
        self.assertIn('title', header)
        self.assertIn('description', header)
        self.assertIn('created_at', header)
        self.assertIn('last_modified', header)
        self.assertIn('tags', header)
        self.assertIn('metric.datasets', header)

        rows = list(reader)
        ids = [row[0] for row in rows]

        # Should ignore paging
        self.assertEqual(len(rows), len(filtered_reuses))
        # SHoulf pass filter
        for reuse in filtered_reuses:
            self.assertIn(str(reuse.id), ids)
        for reuse in reuses:
            self.assertNotIn(str(reuse.id), ids)
        self.assertNotIn(str(hidden_reuse.id), ids)

    def test_harvest_csv(self):
        self.app.config['EXPORT_CSV_MODELS'] = []
        organization = OrganizationFactory()
        harvests = [HarvestSource.objects.create(
            name='harvest',
            url=f'https://example.com/{i}',
            organization=organization
            )
                  for i in range(5)]
        hidden_harvest = HarvestSource.objects.create(
            url='https://example.com/deleted',
            deleted=datetime.now()
        )

        response = self.get(url_for('site.harvests_csv'))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO(response.data.decode('utf8'))
        reader = csv.get_reader(csvfile)
        header = next(reader)

        self.assertEqual(header[0], 'id')
        self.assertIn('name', header)
        self.assertIn('url', header)
        self.assertIn('organization', header)
        self.assertIn('organization_id', header)
        self.assertIn('backend', header)
        self.assertIn('created_at', header)
        self.assertIn('validation', header)

        rows = list(reader)
        ids = [row[0] for row in rows]

        self.assertEqual(len(rows), len(harvests))
        for harvest in harvests:
            self.assertIn(str(harvest.id), ids)
        self.assertNotIn(str(hidden_harvest.id), ids)

    @pytest.mark.usefixtures('instance_path')
    def test_harvest_csv_w_export_csv_feature(self):
        # no export generated, 404
        response = self.get(url_for('site.harvests_csv'))
        self.assert404(response)

        # generate the export
        d = DatasetFactory()
        self.app.config['EXPORT_CSV_DATASET_ID'] = d.id
        dataset_tasks.export_csv()
        response = self.get(url_for('site.harvests_csv'))
        self.assertStatus(response, 302)
        self.assertIn('export-harvest-', response.location)

    def test_terms_view(self):
        response = self.client.get(url_for('site.terms'))
        self.assert200(response)
