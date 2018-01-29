# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
from datetime import datetime, timedelta

from mongoengine import post_save

from udata.models import db, Dataset, License, LEGACY_FREQUENCIES
from udata.core.dataset.factories import (
    ResourceFactory, DatasetFactory, CommunityResourceFactory, LicenseFactory
)
from udata.core.discussions.factories import (
    MessageDiscussionFactory, DiscussionFactory
)
from udata.core.user.factories import UserFactory
from udata.tests.helpers import assert_emit

from .. import TestCase, DBTestMixin


class DatasetModelTest(TestCase, DBTestMixin):
    def test_add_resource(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        resource = ResourceFactory()
        expected_signals = post_save, Dataset.after_save, Dataset.on_update

        with assert_emit(*expected_signals):
            dataset.add_resource(ResourceFactory())
        self.assertEqual(len(dataset.resources), 1)

        with assert_emit(*expected_signals):
            dataset.add_resource(resource)
        self.assertEqual(len(dataset.resources), 2)
        self.assertEqual(dataset.resources[0].id, resource.id)

    def test_add_resource_without_checksum(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        resource = ResourceFactory(checksum=None)
        expected_signals = post_save, Dataset.after_save, Dataset.on_update

        with assert_emit(*expected_signals):
            dataset.add_resource(ResourceFactory(checksum=None))
        self.assertEqual(len(dataset.resources), 1)

        with assert_emit(*expected_signals):
            dataset.add_resource(resource)
        self.assertEqual(len(dataset.resources), 2)
        self.assertEqual(dataset.resources[0].id, resource.id)

    def test_add_resource_missing_checksum_type(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        resource = ResourceFactory()
        resource.checksum.type = None

        with self.assertRaises(db.ValidationError):
            dataset.add_resource(resource)

    def test_update_resource(self):
        user = UserFactory()
        resource = ResourceFactory()
        dataset = DatasetFactory(owner=user, resources=[resource])
        expected_signals = post_save, Dataset.after_save, Dataset.on_update

        resource.description = 'New description'

        with assert_emit(*expected_signals):
            dataset.update_resource(resource)
        self.assertEqual(len(dataset.resources), 1)
        self.assertEqual(dataset.resources[0].id, resource.id)
        self.assertEqual(dataset.resources[0].description, 'New description')

    def test_update_resource_missing_checksum_type(self):
        user = UserFactory()
        resource = ResourceFactory()
        dataset = DatasetFactory(owner=user, resources=[resource])
        resource.checksum.type = None

        with self.assertRaises(db.ValidationError):
            dataset.update_resource(resource)

    def test_last_update_with_resource(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        resource = ResourceFactory()
        dataset.add_resource(resource)
        self.assertEqualDates(dataset.last_update, resource.published)

    def test_last_update_without_resource(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        self.assertEqualDates(dataset.last_update, dataset.last_modified)

    def test_community_resource(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        community_resource1 = CommunityResourceFactory()
        community_resource1.dataset = dataset
        community_resource1.save()
        self.assertEqual(len(dataset.community_resources), 1)

        community_resource2 = CommunityResourceFactory()
        community_resource2.dataset = dataset
        community_resource2.save()
        self.assertEqual(len(dataset.community_resources), 2)
        self.assertEqual(dataset.community_resources[1].id,
                         community_resource1.id)
        self.assertEqual(dataset.community_resources[0].id,
                         community_resource2.id)

    def test_next_update_empty(self):
        dataset = DatasetFactory()
        self.assertEqual(dataset.next_update, None)

    def test_next_update_weekly(self):
        dataset = DatasetFactory(frequency='weekly')
        self.assertEqualDates(dataset.next_update,
                              datetime.now() + timedelta(days=7))

    def test_quality_default(self):
        dataset = DatasetFactory(description='')
        self.assertEqual(dataset.quality, {'score': 0})

    def test_quality_next_update(self):
        dataset = DatasetFactory(description='', frequency='weekly')
        self.assertEqual(-6, dataset.quality['update_in'])
        self.assertEqual(dataset.quality['frequency'], 'weekly')
        self.assertEqual(dataset.quality['score'], 2)

    def test_quality_tags_count(self):
        dataset = DatasetFactory(description='', tags=['foo', 'bar'])
        self.assertEqual(dataset.quality['tags_count'], 2)
        self.assertEqual(dataset.quality['score'], 0)
        dataset = DatasetFactory(description='',
                                 tags=['foo', 'bar', 'baz', 'quux'])
        self.assertEqual(dataset.quality['score'], 2)

    def test_quality_description_length(self):
        dataset = DatasetFactory(description='a' * 42)
        self.assertEqual(dataset.quality['description_length'], 42)
        self.assertEqual(dataset.quality['score'], 0)
        dataset = DatasetFactory(description='a' * 420)
        self.assertEqual(dataset.quality['score'], 2)

    def test_quality_has_only_closed_formats(self):
        dataset = DatasetFactory(description='', )
        dataset.add_resource(ResourceFactory(format='pdf'))
        self.assertTrue(dataset.quality['has_only_closed_or_no_formats'])
        self.assertEqual(dataset.quality['score'], 0)

    def test_quality_has_opened_formats(self):
        dataset = DatasetFactory(description='', )
        dataset.add_resource(ResourceFactory(format='pdf'))
        dataset.add_resource(ResourceFactory(format='csv'))
        self.assertFalse(dataset.quality['has_only_closed_or_no_formats'])
        self.assertEqual(dataset.quality['score'], 4)

    def test_quality_has_undefined_and_closed_format(self):
        dataset = DatasetFactory(description='', )
        dataset.add_resource(ResourceFactory(format=None))
        dataset.add_resource(ResourceFactory(format='xls'))
        self.assertTrue(dataset.quality['has_only_closed_or_no_formats'])
        self.assertEqual(dataset.quality['score'], 0)

    def test_quality_has_untreated_discussions(self):
        user = UserFactory()
        visitor = UserFactory()
        dataset = DatasetFactory(description='', owner=user)
        messages = MessageDiscussionFactory.build_batch(2, posted_by=visitor)
        DiscussionFactory(subject=dataset, user=visitor, discussion=messages)
        self.assertEqual(dataset.quality['discussions'], 1)
        self.assertTrue(dataset.quality['has_untreated_discussions'])
        self.assertEqual(dataset.quality['score'], 0)

    def test_quality_has_treated_discussions(self):
        user = UserFactory()
        visitor = UserFactory()
        dataset = DatasetFactory(description='', owner=user)
        DiscussionFactory(
            subject=dataset, user=visitor,
            discussion=[
                MessageDiscussionFactory(posted_by=user)
            ] + MessageDiscussionFactory.build_batch(2, posted_by=visitor)
        )
        self.assertEqual(dataset.quality['discussions'], 1)
        self.assertFalse(dataset.quality['has_untreated_discussions'])
        self.assertEqual(dataset.quality['score'], 2)

    def test_quality_all(self):
        user = UserFactory()
        visitor = UserFactory()
        dataset = DatasetFactory(owner=user, frequency='weekly',
                                 tags=['foo', 'bar'], description='a' * 42)
        dataset.add_resource(ResourceFactory(format='pdf'))
        DiscussionFactory(
            subject=dataset, user=visitor,
            discussion=[MessageDiscussionFactory(posted_by=visitor)])
        self.assertEqual(dataset.quality['score'], 0)
        self.assertEqual(
            sorted(dataset.quality.keys()),
            [
                'description_length',
                'discussions',
                'frequency',
                'has_only_closed_or_no_formats',
                'has_resources',
                'has_unavailable_resources',
                'has_untreated_discussions',
                'score',
                'tags_count',
                'update_in'
            ])

    def test_tags_normalized(self):
        tags = [' one another!', ' one another!', 'This IS a "tag"…']
        dataset = DatasetFactory(tags=tags)
        self.assertEqual(len(dataset.tags), 2)
        self.assertEqual(dataset.tags[1], 'this-is-a-tag')

    def test_legacy_frequencies(self):
        for oldFreq, newFreq in LEGACY_FREQUENCIES.items():
            dataset = DatasetFactory(frequency=oldFreq)
            self.assertEqual(dataset.frequency, newFreq)

    def test_send_on_delete(self):
        dataset = DatasetFactory()
        with assert_emit(Dataset.on_delete):
            dataset.deleted = datetime.now()
            dataset.save()


class ResourceModelTest(TestCase, DBTestMixin):
    def test_url_is_required(self):
        with self.assertRaises(db.ValidationError):
            DatasetFactory(resources=[ResourceFactory(url=None)])

    def test_bad_url(self):
        with self.assertRaises(db.ValidationError):
            DatasetFactory(resources=[ResourceFactory(url='not-an-url')])

    def test_url_is_stripped(self):
        url = 'http://www.somewhere.com/with/spaces/   '
        dataset = DatasetFactory(resources=[ResourceFactory(url=url)])
        self.assertEqual(dataset.resources[0].url, url.strip())


class LicenseModelTest(DBTestMixin, TestCase):
    def setUp(self):
        # Feed the DB with random data to ensure true matching
        LicenseFactory.create_batch(3)

    def test_not_found(self):
        found = License.guess('should not be found')
        self.assertIsNone(found)

    def test_not_found_with_default(self):
        license = LicenseFactory()
        found = License.guess('should not be found', default=license)
        self.assertEqual(found.id, license.id)

    def test_none(self):
        found = License.guess(None)
        self.assertIsNone(found)

    def test_empty_string(self):
        found = License.guess('')
        self.assertIsNone(found)

    def test_exact_match_by_id(self):
        license = LicenseFactory()
        found = License.guess(license.id)
        self.assertIsInstance(found, License)
        self.assertEqual(license.id, found.id)

    def test_exact_match_by_id_with_spaces(self):
        license = LicenseFactory()
        found = License.guess(' {0} '.format(license.id))
        self.assertIsInstance(found, License)
        self.assertEqual(license.id, found.id)

    def test_exact_match_by_url(self):
        license = LicenseFactory()
        found = License.guess(license.url)
        self.assertIsInstance(found, License)
        self.assertEqual(license.id, found.id)

    def test_exact_match_by_title(self):
        license = LicenseFactory()
        found = License.guess(license.title)
        self.assertIsInstance(found, License)
        self.assertEqual(license.id, found.id)

    def test_exact_match_by_title_with_spaces(self):
        license = LicenseFactory()
        found = License.guess(' {0} '.format(license.title))
        self.assertIsInstance(found, License)
        self.assertEqual(license.id, found.id)

    def test_match_by_title_with_low_edit_distance(self):
        license = LicenseFactory(title='License')
        found = License.guess('Licence')
        self.assertIsInstance(found, License)
        self.assertEqual(license.id, found.id)

    def test_match_by_title_with_extra_inner_space(self):
        license = LicenseFactory(title='License ODBl')
        found = License.guess('License  ODBl')  # 2 spaces instead of 1
        self.assertIsInstance(found, License)
        self.assertEqual(license.id, found.id)

    def test_match_by_title_with_mismatching_case(self):
        license = LicenseFactory(title='License ODBl')
        found = License.guess('License ODBL')
        self.assertIsInstance(found, License)
        self.assertEqual(license.id, found.id)

    def test_multiple_strings(self):
        license = LicenseFactory()
        found = License.guess('should not match', license.id)
        self.assertIsInstance(found, License)
        self.assertEqual(license.id, found.id)
