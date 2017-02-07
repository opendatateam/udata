# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import json

from uuid import uuid4, UUID
from datetime import date, datetime, timedelta

from mongoengine.errors import ValidationError

from udata.models import db, Dataset
from udata.tests import TestCase, DBTestMixin


class UUIDTester(db.Document):
    uuid = db.AutoUUIDField()


class UUIDAsIdTester(db.Document):
    id = db.AutoUUIDField(primary_key=True)


class SlugTester(db.Document):
    title = db.StringField()
    slug = db.SlugField(populate_from='title', max_length=1000)
    meta = {
        'allow_inheritance': True,
    }


class SlugUpdateTester(db.Document):
    title = db.StringField()
    slug = db.SlugField(populate_from='title', update=True)


class DateTester(db.Document):
    a_date = db.DateField()


class DateTesterWithDefault(db.Document):
    a_date = db.DateField(default=date.today)


class InheritedSlugTester(SlugTester):
    other = db.StringField()


class DatetimedTester(db.Datetimed, db.Document):
    name = db.StringField()


class AutoUUIDFieldTest(TestCase):
    def test_auto_populate(self):
        '''AutoUUIDField should populate itself if not set'''
        obj = UUIDTester()
        self.assertIsNotNone(obj.uuid)
        self.assertIsInstance(obj.uuid, UUID)

    def test_do_not_overwrite(self):
        '''AutoUUIDField shouldn't populate itself if a value is already set'''
        uuid = uuid4()
        obj = UUIDTester(uuid=uuid)
        self.assertEqual(obj.uuid, uuid)

    def test_as_primary_key(self):
        obj = UUIDAsIdTester()
        self.assertIsNotNone(obj.id)
        self.assertIsInstance(obj.id, UUID)
        self.assertEqual(obj.pk, obj.id)


class SlugFieldTest(DBTestMixin, TestCase):
    def test_validate(self):
        '''SlugField should validate if not set'''
        obj = SlugTester(title="A Title")
        self.assertIsNone(obj.slug)
        obj.validate()

    def test_populate(self):
        '''SlugField should populate itself on save if not set'''
        obj = SlugTester(title="A Title")
        self.assertIsNone(obj.slug)
        obj.save()
        self.assertEqual(obj.slug, 'a-title')

    def test_populate_next(self):
        '''SlugField should not keep other fields value'''
        obj = SlugTester.objects.create(title="A Title")
        obj.slug = 'fake'
        obj = SlugTester.objects.create(title="Another title")
        self.assertEqual(obj.slug, 'another-title')

    def test_populate_parallel(self):
        '''SlugField should not take other instance values'''
        obj1 = SlugTester.objects.create(title="A Title")
        obj = SlugTester.objects.create(title="Another title")
        obj1.slug = 'fake'
        self.assertEqual(obj.slug, 'another-title')

    def test_no_populate(self):
        '''SlugField should not populate itself if a value is set'''
        obj = SlugTester(title='A Title', slug='a-slug')
        obj.save()
        self.assertEqual(obj.slug, 'a-slug')

    def test_populate_update(self):
        '''SlugField should populate itself on save and update'''
        obj = SlugUpdateTester(title="A Title")
        obj.save()
        self.assertEqual(obj.slug, 'a-title')
        obj.title = 'Title'
        obj.save()
        self.assertEqual(obj.slug, 'title')

    def test_no_populate_update(self):
        '''SlugField should not populate itself if a value is set'''
        obj = SlugUpdateTester(title="A Title")
        obj.save()
        self.assertEqual(obj.slug, 'a-title')
        obj.title = 'Title'
        obj.slug = 'other'
        obj.save()
        self.assertEqual(obj.slug, 'other')

    def test_unchanged(self):
        '''SlugField should not chnage on save if not needed'''
        obj = SlugTester(title="A Title")
        self.assertIsNone(obj.slug)
        obj.save()
        self.assertEqual(obj.slug, 'a-title')
        obj.save()
        self.assertEqual(obj.slug, 'a-title')

    def test_changed_no_update(self):
        '''SlugField should not update slug if update=False'''
        obj = SlugTester(title="A Title")
        obj.save()
        self.assertEqual(obj.slug, 'a-title')
        obj.title = 'Title'
        obj.save()
        self.assertEqual(obj.slug, 'a-title')

    def test_manually_set(self):
        '''SlugField can be manually set'''
        obj = SlugTester(title='A title', slug='a-slug')
        self.assertEqual(obj.slug, 'a-slug')
        obj.save()
        self.assertEqual(obj.slug, 'a-slug')

    def test_work_accross_inheritance(self):
        '''SlugField should ensure uniqueness accross inheritance'''
        obj = SlugTester.objects.create(title='title')
        inherited = InheritedSlugTester.objects.create(title='title')
        self.assertNotEqual(obj.slug, inherited.slug)

    def test_crop(self):
        '''SlugField should truncate itself on save if not set'''
        obj = SlugTester(title='x' * (SlugTester.slug.max_length + 1))
        obj.save()
        self.assertEqual(len(obj.title), SlugTester.slug.max_length + 1)
        self.assertEqual(len(obj.slug), SlugTester.slug.max_length)


class DateFieldTest(DBTestMixin, TestCase):
    def test_none_if_empty_and_not_required(self):
        obj = DateTester()
        self.assertIsNone(obj.a_date)
        obj.save()
        obj.reload()
        self.assertIsNone(obj.a_date)

    def test_default(self):
        today = date.today()
        obj = DateTesterWithDefault()
        self.assertEqual(obj.a_date, today)
        obj.save()
        obj.reload()
        self.assertEqual(obj.a_date, today)

    def test_date(self):
        the_date = date(1984, 6, 6)
        obj = DateTester(a_date=the_date)
        self.assertEqual(obj.a_date, the_date)
        obj.save()
        obj.reload()
        self.assertEqual(obj.a_date, the_date)

    def test_not_valid(self):
        obj = DateTester(a_date='invalid')
        with self.assertRaises(ValidationError):
            obj.save()


class DatetimedTest(DBTestMixin, TestCase):
    def test_class(self):
        self.assertIsInstance(DatetimedTester.created_at, db.DateTimeField)
        self.assertIsInstance(DatetimedTester.last_modified, db.DateTimeField)

    def test_new_instance(self):
        now = datetime.now()
        datetimed = DatetimedTester()

        self.assertGreaterEqual(datetimed.created_at, now)
        self.assertLessEqual(datetimed.created_at, datetime.now())

        self.assertGreaterEqual(datetimed.last_modified, now)
        self.assertLessEqual(datetimed.last_modified, datetime.now())

    def test_save_new_instance(self):
        now = datetime.now()
        datetimed = DatetimedTester.objects.create()

        self.assertGreaterEqual(datetimed.created_at, now)
        self.assertLessEqual(datetimed.created_at, datetime.now())

        self.assertGreaterEqual(datetimed.last_modified, now)
        self.assertLessEqual(datetimed.last_modified, datetime.now())

    def test_save_last_modified_instance(self):
        now = datetime.now()
        earlier = now - timedelta(days=1)
        datetimed = DatetimedTester.objects.create(
            created_at=earlier, last_modified=earlier)

        datetimed.save()

        self.assertEqual(datetimed.created_at, earlier)

        self.assertGreaterEqual(datetimed.last_modified, now)
        self.assertLessEqual(datetimed.last_modified, datetime.now())


class ExtrasField(DBTestMixin, TestCase):
    def test_default_validate(self):
        class Tester(db.Document):
            extras = db.ExtrasField()

        now = datetime.now()
        today = date.today()

        tester = Tester(extras={
            'string': 'string',
            'integer': 5,
            'float': 5.5,
            'datetime': now,
            'date': today,
            'bool': True
        })
        tester.validate()

    def test_validate_unregistered_type(self):
        class Tester(db.Document):
            extras = db.ExtrasField()

        tester = Tester(extras={'dict': {}})

        with self.assertRaises(ValidationError):
            tester.validate()

    def test_validate_registered_type(self):
        class Tester(db.Document):
            extras = db.ExtrasField()

        @Tester.extras('test')
        class ExtraDict(db.Extra):
            def validate(self, value):
                if not isinstance(value, dict):
                    raise db.ValidationError('Should be a dict instance')

        tester = Tester(extras={'test': {}})
        tester.validate()

    def test_validate_registered_type_embedded_document(self):
        class Tester(db.Document):
            extras = db.ExtrasField()

        @Tester.extras('test')
        class EmbeddedExtra(db.EmbeddedDocument):
            name = db.StringField(required=True)

        tester = Tester(extras={'test': {}})
        with self.assertRaises(ValidationError):
            tester.validate()

        tester.extras['test'] = {'name': 'test'}
        tester.validate()

        tester.extras['test'] = EmbeddedExtra(name='test')
        tester.validate()

    def test_is_json_serializable(self):
        class Tester(db.Document):
            extras = db.ExtrasField()

        @Tester.extras('dict')
        class ExtraDict(db.Extra):
            def validate(self, value):
                if not isinstance(value, dict):
                    raise db.ValidationError('Should be a dict instance')

        @Tester.extras('embedded')
        class EmbeddedExtra(db.EmbeddedDocument):
            name = db.StringField(required=True)

        tester = Tester(extras={
            'test': {'key': 'value'},
            'embedded': EmbeddedExtra(name='An embedded field'),
            'string': 'a value',
            'integer': 5,
            'float': 5.5,
        })

        self.assertEqual(json.dumps(tester.extras), json.dumps({
            'test': {'key': 'value'},
            'embedded': {'name': 'An embedded field'},
            'string': 'a value',
            'integer': 5,
            'float': 5.5,
        }))


class ModelResolutionTest(DBTestMixin, TestCase):
    def test_resolve_exact_match(self):
        self.assertEqual(db.resolve_model('Dataset'), Dataset)

    def test_resolve_from_dict(self):
        self.assertEqual(db.resolve_model({'class': 'Dataset'}), Dataset)

    def test_raise_if_not_found(self):
        with self.assertRaises(db.NotRegistered):
            db.resolve_model('NotFound')

    def test_raise_if_not_a_document(self):
        with self.assertRaises(db.NotRegistered):
            db.resolve_model('UDataMongoEngine')

    def test_raise_if_none(self):
        with self.assertRaises(ValueError):
            db.resolve_model(None)

    def test_raise_if_missing_class_entry(self):
        with self.assertRaises(ValueError):
            db.resolve_model({'field': 'value'})
