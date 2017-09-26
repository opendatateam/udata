# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import StringIO

import factory

from random import randint

from factory.mongoengine import MongoEngineFactory

from flask import url_for, Blueprint

from udata.models import db
from udata.core.metrics import Metric, init_app as init_metrics
from udata.frontend import csv
from udata.utils import faker

from . import FrontTestCase


RE_ATTACHMENT = re.compile(r'^attachment; filename=(?P<filename>.*)$')
RE_FILENAME = re.compile(
    r'^(?P<basename>.*)-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}\.csv$')


blueprint = Blueprint('testcsv', __name__)


class NestedFake(db.EmbeddedDocument):
    key = db.StringField()
    value = db.IntField()


class Fake(db.Document):
    title = db.StringField()
    description = db.StringField()
    tags = db.ListField(db.StringField())
    other = db.ListField(db.StringField())
    nested = db.ListField(db.EmbeddedDocumentField(NestedFake))
    sub = db.EmbeddedDocumentField(NestedFake)
    metrics = db.DictField()

    def __unicode__(self):
        return 'fake'


class FakeMetricInt(Metric):
    model = Fake
    name = 'fake-metric-int'


class FakeMetricFloat(Metric):
    model = Fake
    name = 'fake-metric-float'
    value_type = float


class NestedFactory(MongoEngineFactory):
    class Meta:
        model = NestedFake

    key = factory.LazyAttribute(lambda o: faker.word())
    value = factory.LazyAttribute(lambda o: faker.pyint())


class FakeFactory(MongoEngineFactory):
    class Meta:
        model = Fake

    title = factory.LazyAttribute(lambda o: faker.sentence())
    description = factory.LazyAttribute(lambda o: faker.paragraph())
    tags = factory.LazyAttribute(
        lambda o: [faker.word() for _ in range(1, randint(1, 4))])
    sub = factory.SubFactory(NestedFactory)


class NestedAdapter(csv.NestedAdapter):
    attribute = 'nested'
    fields = (
        'title',
        'description',
    )
    nested_fields = (
        'key',
        ('alias', 'value'),
    )


@blueprint.route('/adapter.csv')
def from_adapter():
    cls = csv.get_adapter(Fake)
    adapter = cls(Fake.objects)
    return csv.stream(adapter)


@blueprint.route('/list.csv')
def from_list():
    return csv.stream(list(Fake.objects))


@blueprint.route('/queryset.csv')
def from_queryset():
    qs = Fake.objects
    assert isinstance(qs, db.BaseQuerySet)
    return csv.stream(qs)


@blueprint.route('/nested.csv')
def from_nested():
    qs = Fake.objects
    return csv.stream(NestedAdapter(qs))


@blueprint.route('/with-basename.csv')
def with_basename():
    cls = csv.get_adapter(Fake)
    adapter = cls(Fake.objects)
    return csv.stream(adapter, 'test')


class CsvTest(FrontTestCase):
    modules = ['admin', 'core.dataset', 'core.reuse', 'core.site',
               'core.organization', 'search']

    def create_app(self):
        app = super(CsvTest, self).create_app()
        init_metrics(app)
        app.register_blueprint(blueprint)
        return app

    def test_adapter_fields_as_list(self):
        @csv.adapter(Fake)
        class Adapter(csv.Adapter):
            fields = ['title', 'description']

        objects = FakeFactory.build_batch(3)
        adapter = Adapter(objects)

        header = adapter.header()
        self.assertEqual(header, ['title', 'description'])

        rows = list(adapter.rows())
        self.assertEqual(len(rows), len(objects))
        for obj, row in zip(objects, rows):
            self.assertEqual(len(row), len(header))
            self.assertEqual(row[0], obj.title)
            self.assertEqual(row[1], obj.description)

    def test_adapter_fields_as_list_with_nested(self):
        @csv.adapter(Fake)
        class Adapter(csv.Adapter):
            fields = ['title', 'description', 'sub.key']

        objects = FakeFactory.build_batch(3)
        adapter = Adapter(objects)

        header = adapter.header()
        self.assertEqual(header, ['title', 'description', 'sub.key'])

        rows = list(adapter.rows())
        self.assertEqual(len(rows), len(objects))
        for obj, row in zip(objects, rows):
            self.assertEqual(len(row), len(header))
            self.assertEqual(row[0], obj.title)
            self.assertEqual(row[1], obj.description)
            self.assertEqual(row[2], obj.sub.key)

    def test_adapter_fields_as_mixed_list(self):
        @csv.adapter(Fake)
        class Adapter(csv.Adapter):
            fields = (
                'title',
                'description',
                ('tags', lambda o: ','.join(o.tags)),
                ('alias', 'title'),
            )

        objects = FakeFactory.build_batch(3)
        adapter = Adapter(objects)

        header = adapter.header()
        self.assertEqual(header, ['title', 'description', 'tags', 'alias'])

        rows = list(adapter.rows())
        self.assertEqual(len(rows), len(objects))
        for obj, row in zip(objects, rows):
            self.assertEqual(len(row), len(header))
            self.assertEqual(row[0], obj.title)
            self.assertEqual(row[1], obj.description)
            self.assertEqual(row[2], ','.join(obj.tags))
            self.assertEqual(row[3], obj.title)

    def test_adapter_fields_with_method(self):
        @csv.adapter(Fake)
        class Adapter(csv.Adapter):
            fields = (
                'title',
                'description',
                'tags'
            )

            def field_tags(self, obj):
                return ','.join(obj.tags)

        objects = FakeFactory.build_batch(3)
        adapter = Adapter(objects)

        header = adapter.header()
        self.assertEqual(header, ['title', 'description', 'tags'])

        rows = list(adapter.rows())
        self.assertEqual(len(rows), len(objects))
        for obj, row in zip(objects, rows):
            self.assertEqual(len(row), len(header))
            self.assertEqual(row[0], obj.title)
            self.assertEqual(row[1], obj.description)
            self.assertEqual(row[2], ','.join(obj.tags))

    def test_adapter_fields_with_dyanmic_fields(self):
        @csv.adapter(Fake)
        class Adapter(csv.Adapter):
            fields = (
                'title',
            )

            def dynamic_fields(self):
                return (
                    'description',
                    ('alias', 'title'),
                    ('tags', lambda o: ','.join(o.tags)),
                )

        objects = FakeFactory.build_batch(3)
        adapter = Adapter(objects)

        header = adapter.header()
        self.assertEqual(header, ['title', 'description', 'alias', 'tags'])

        rows = list(adapter.rows())
        self.assertEqual(len(rows), len(objects))
        for obj, row in zip(objects, rows):
            self.assertEqual(len(row), len(header))
            self.assertEqual(row[0], obj.title)
            self.assertEqual(row[1], obj.description)
            self.assertEqual(row[2], obj.title)
            self.assertEqual(row[3], ','.join(obj.tags))

    def test_metric_fields(self):
        expected = {
            'metric.fake-metric-int': 5,
            'metric.fake-metric-float': 0.5,
        }
        fake = FakeFactory(
            metrics={'fake-metric-int': 5, 'fake-metric-float': 0.5})

        fields = csv.metric_fields(Fake)
        self.assertEqual(len(fields), len(expected))
        for name, getter in fields:
            self.assertIn(name, expected.keys())
            self.assertEqual(getter(fake), expected[name])

    def test_unicode(self):
        @csv.adapter(Fake)
        class Adapter(csv.Adapter):
            fields = ['title', 'description']

        objects = FakeFactory.build_batch(3, description='é\xe9')
        adapter = Adapter(objects)

        header = adapter.header()
        self.assertEqual(header, ['title', 'description'])

        rows = list(adapter.rows())
        self.assertEqual(len(rows), len(objects))
        for obj, row in zip(objects, rows):
            self.assertEqual(len(row), len(header))
            self.assertEqual(row[0], obj.title)
            self.assertEqual(row[1], obj.description)

    def assert_stream_csv(self, endpoint):
        return self.assert_csv(endpoint, [FakeFactory() for _ in range(3)])

    def assert_empty_stream_csv(self, endpoint):
        return self.assert_csv(endpoint, [])

    def assert_csv(self, endpoint, objects):
        @csv.adapter(Fake)
        class Adapter(csv.Adapter):
            fields = ['title', 'description']

        response = self.get(url_for(endpoint))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO.StringIO(response.data)
        reader = csv.get_reader(csvfile)
        header = reader.next()
        self.assertEqual(header, ['title', 'description'])

        rows = list(reader)
        self.assertEqual(len(rows), len(objects))
        for row, obj in zip(rows, objects):
            self.assertEqual(len(row), len(header))
            self.assertEqual(row[0], obj.title)
            self.assertEqual(row[1], obj.description)

        return response

    def assert_filename(self, response, basename):
        header = response.headers['Content-Disposition']
        m = RE_ATTACHMENT.match(header)
        self.assertIsNotNone(
            m,
            'Content-Disposition header should specify a filename attachment')
        filename = m.group('filename')
        m = RE_FILENAME.match(filename)
        self.assertIsNotNone(m, 'filename should have the right pattern')
        self.assertEqual(m.group('basename'), basename)

    def test_stream_from_adapter(self):
        response = self.assert_stream_csv('testcsv.from_adapter')
        self.assert_filename(response, 'export')

    def test_stream_from_queryset(self):
        response = self.assert_stream_csv('testcsv.from_queryset')
        self.assert_filename(response, 'export')

    def test_stream_from_list(self):
        response = self.assert_stream_csv('testcsv.from_list')
        self.assert_filename(response, 'export')

    def test_stream_with_basename(self):
        response = self.assert_stream_csv('testcsv.with_basename')
        self.assert_filename(response, 'test')

    def test_empty_stream_from_adapter(self):
        response = self.assert_empty_stream_csv('testcsv.from_adapter')
        self.assert_filename(response, 'export')

    def test_empty_stream_from_queryset(self):
        response = self.assert_empty_stream_csv('testcsv.from_queryset')
        self.assert_filename(response, 'export')

    def test_empty_stream_from_list(self):
        self.assert400(self.get(url_for('testcsv.from_list')))

    def test_stream_nested_from_adapter(self):
        fake = FakeFactory.build()
        for i in range(3):
            fake.nested.append(NestedFake(key=faker.word(), value=i))
        fake.save()
        response = self.get(url_for('testcsv.from_nested'))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO.StringIO(response.data)
        reader = csv.get_reader(csvfile)
        header = reader.next()
        self.assertEqual(header, ['title', 'description', 'key', 'alias'])

        rows = list(reader)
        self.assertEqual(len(rows), len(fake.nested))
        for row, obj in zip(rows, fake.nested):
            self.assertEqual(len(row), len(header))
            self.assertEqual(row[0], fake.title)
            self.assertEqual(row[1], fake.description)
            self.assertEqual(row[2], obj.key)
            self.assertEqual(row[3], str(obj.value))

    def test_stream_unicode(self):
        fake = FakeFactory(title='é\xe9')
        response = self.get(url_for('testcsv.from_adapter'))

        self.assert200(response)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertEqual(response.charset, 'utf-8')

        csvfile = StringIO.StringIO(response.data)
        reader = csv.get_reader(csvfile)
        header = reader.next()
        self.assertEqual(header, ['title', 'description'])

        row = reader.next()
        self.assertEqual(len(row), len(header))
        self.assertEqual(row[0], fake.title)
        self.assertEqual(row[1], fake.description)
