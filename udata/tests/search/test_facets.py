from datetime import date, timedelta

import factory
import pytest

from elasticsearch_dsl import Q, A

from udata import search
from udata.i18n import gettext as _, format_date
from udata.models import db
from udata.utils import faker

from . import response_factory, FakeSearchable, FakeFactory


class FakeWithStringId(FakeSearchable):
    id = db.StringField(primary_key=True)


class FakeWithStringIdFactory(FakeFactory):
    id = factory.Faker('unique_string')

    class Meta:
        model = FakeWithStringId


def bucket_agg_factory(buckets):
    return {
        'test': {
            'buckets': buckets,
            'doc_count_error_upper_bound': 1,
            'sum_other_doc_count': 94,
        }
    }


@pytest.mark.usefixtures('autoindex')
class FacetTestCase:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.setUp()

    def factory(self, **kwargs):
        '''
        Build a fake Elasticsearch DSL FacetedResponse
        and extract the facet form it
        '''
        data = response_factory(**kwargs)

        class TestSearch(search.SearchQuery):
            facets = {
                'test': self.facet
            }

        s = TestSearch({})
        response = search.SearchResult(s, data)
        return response.facets.test


class BoolFacetTest(FacetTestCase):
    def setUp(self):
        self.facet = search.BoolFacet(field='boolean')

    def test_get_values(self):
        buckets = [
            {'key': 'T', 'doc_count': 10},
            {'key': 'F', 'doc_count': 15},
        ]
        result = self.factory(aggregations=bucket_agg_factory(buckets))

        assert len(result) == 2
        for row in result:
            assert isinstance(row[0], bool)
            assert isinstance(row[1], int)
            assert isinstance(row[2], bool)
        # Assume order is buckets' order
        assert result[0][0]
        assert result[0][1] == 10
        assert not result[1][0]
        assert result[1][1] == 15

    def test_value_filter(self):
        for value in True, 'True', 'true':
            expected = Q({'term': {'boolean': True}})
            value_filter = self.facet.get_value_filter(value)
            assert value_filter == expected

        for value in False, 'False', 'false':
            expected = ~Q({'term': {'boolean': True}})
            value_filter = self.facet.get_value_filter(value)
            assert value_filter == expected

    def test_aggregation(self):
        expected = A({'terms': {'field': 'boolean'}})
        assert self.facet.get_aggregation() == expected

    def test_labelize(self):
        assert self.facet.labelize(True) == _('yes')
        assert self.facet.labelize(False) == _('no')

        assert self.facet.labelize('true') == _('yes')
        assert self.facet.labelize('false') == _('no')


class TermsFacetTest(FacetTestCase):
    def setUp(self):
        self.facet = search.TermsFacet(field='tags')

    def test_get_values(self):
        buckets = [{
            'key': faker.word(),
            'doc_count': faker.random_number(2)
        } for _ in range(10)]
        result = self.factory(aggregations=bucket_agg_factory(buckets))

        assert len(result) == 10
        for row in result:
            assert isinstance(row[0], str)
            assert isinstance(row[1], int)
            assert isinstance(row[2], bool)

    def test_labelize(self):
        assert self.facet.labelize('fake') == 'fake'

    def test_labelize_unicode(self):
        assert self.facet.labelize('é') == 'é'

    def test_labelize_with_or(self):
        assert self.facet.labelize('fake-1|fake-2') == 'fake-1 OR fake-2'

    def test_labelize_with_or_and_custom_labelizer(self):
        labelizer = lambda v: 'custom-{0}'.format(v)  # noqa: E731
        facet = search.TermsFacet(field='tags', labelizer=labelizer)
        assert facet.labelize('fake-1|fake-2') == 'custom-fake-1 OR custom-fake-2'

    def test_filter_and(self):
        values = ['tag-1', 'tag-2']
        expected = Q('bool', must=[
            Q('term', tags='tag-1'),
            Q('term', tags='tag-2'),
        ])
        assert self.facet.add_filter(values) == expected

    def test_filter_or(self):
        values = ['tag-1|tag-2']
        expected = Q('term', tags='tag-1') | Q('term', tags='tag-2')
        assert self.facet.add_filter(values) == expected

    def test_filter_or_multiple(self):
        values = ['tag-1|tag-2|tag-3']
        expected = Q('bool', should=[
            Q('term', tags='tag-1'),
            Q('term', tags='tag-2'),
            Q('term', tags='tag-3'),
        ])
        assert self.facet.add_filter(values) == expected

    def test_filter_and_or(self):
        values = ['tag-1', 'tag-2|tag-3', 'tag-4|tag-5', 'tag-6']
        expected = Q('bool', must=[
            Q('term', tags='tag-1'),
            Q('term', tags='tag-2') | Q('term', tags='tag-3'),
            Q('term', tags='tag-4') | Q('term', tags='tag-5'),
            Q('term', tags='tag-6'),
        ])
        assert self.facet.add_filter(values) == expected


@pytest.mark.usefixtures('clean_db')
class ModelTermsFacetTest(FacetTestCase):
    def setUp(self):
        self.facet = search.ModelTermsFacet(field='fakes', model=FakeSearchable)

    def test_labelize_id(self):
        fake = FakeFactory()
        assert self.facet.labelize(str(fake.id)) == fake.title

    def test_labelize_object(self):
        fake = FakeFactory()
        assert self.facet.labelize(fake) == fake.title

    def test_labelize_object_with_unicode(self):
        fake = FakeFactory(title='ééé')
        assert self.facet.labelize(fake) == 'ééé'

    def test_labelize_object_with_or(self):
        fake_1 = FakeFactory()
        fake_2 = FakeFactory()
        org_facet = search.ModelTermsFacet(field='id', model=FakeSearchable)
        assert (
            org_facet.labelize('{0}|{1}'.format(fake_1.id, fake_2.id))
            ==
            '{0} OR {1}'.format(fake_1.title, fake_2.title)
        )

    def test_labelize_object_with_or_and_html(self):
        def labelizer(value):
            return FakeSearchable.objects(id=value).first()

        fake_1 = FakeFactory()
        fake_2 = FakeFactory()
        facet = search.ModelTermsFacet(field='id', model=FakeSearchable,
                                       labelizer=labelizer)
        assert (
            facet.labelize('{0}|{1}'.format(fake_1.id, fake_2.id))
            ==
            '<span>{0}</span> OR <span>{1}</span>'.format(fake_1.title,
                                                          fake_2.title)
        )

    def test_get_values(self):
        fakes = [FakeFactory() for _ in range(10)]
        buckets = [{
            'key': str(f.id),
            'doc_count': faker.random_number(2)
        } for f in fakes]
        result = self.factory(aggregations=bucket_agg_factory(buckets))

        assert len(result) == 10
        for fake, row in zip(fakes, result):
            assert isinstance(row[0], FakeSearchable)
            assert isinstance(row[1], int)
            assert isinstance(row[2], bool)
            assert fake.id == row[0].id

    def test_validate_parameters(self):
        fake = FakeFactory()
        for value in [str(fake.id), fake.id]:
            assert self.facet.validate_parameter(value)

        bad_values = ['xyz', True, 42]
        for value in bad_values:
            with pytest.raises(Exception):
                self.facet.validate_parameter(value)

    def test_validate_parameters_with_or(self):
        fake_1 = FakeFactory()
        fake_2 = FakeFactory()
        value = '{0}|{1}'.format(fake_1.id, fake_2.id)
        assert self.facet.validate_parameter(value)


class ModelTermsFacetWithStringIdTest(FacetTestCase):
    def setUp(self):
        self.facet = search.ModelTermsFacet(field='fakes',
                                            model=FakeWithStringId)

    def test_labelize_id(self):
        fake = FakeWithStringIdFactory()
        assert self.facet.labelize(str(fake.id)) == fake.title

    def test_labelize_object(self):
        fake = FakeWithStringIdFactory()
        assert self.facet.labelize(fake) == fake.title

    def test_labelize_object_with_or(self):
        fake_1 = FakeWithStringIdFactory()
        fake_2 = FakeWithStringIdFactory()
        facet = search.ModelTermsFacet(field='id', model=FakeWithStringId)
        assert (
            facet.labelize('{0}|{1}'.format(fake_1.id, fake_2.id))
            ==
            '{0} OR {1}'.format(fake_1.title, fake_2.title)
        )

    def test_labelize_object_with_or_and_html(self):
        def labelizer(value):
            return FakeWithStringId.objects(id=value).first()
        fake_1 = FakeWithStringIdFactory()
        fake_2 = FakeWithStringIdFactory()
        facet = search.ModelTermsFacet(field='id', model=FakeWithStringId,
                                       labelizer=labelizer)
        assert (
            facet.labelize('{0}|{1}'.format(fake_1.id, fake_2.id))
            ==
            '<span>{0}</span> OR <span>{1}</span>'.format(fake_1.title,
                                                          fake_2.title)
        )

    def test_get_values(self):
        fakes = [FakeWithStringIdFactory() for _ in range(10)]
        buckets = [{
            'key': str(f.id),
            'doc_count': faker.random_number(2)
        } for f in fakes]
        result = self.factory(aggregations=bucket_agg_factory(buckets))

        assert len(result) == 10
        for fake, row in zip(fakes, result):
            assert isinstance(row[0], FakeWithStringId)
            assert isinstance(row[1], int)
            assert isinstance(row[2], bool)
            assert fake.id == row[0].id

    def test_validate_parameters(self):
        fake = FakeWithStringIdFactory()
        assert self.facet.validate_parameter(fake.id)

    def test_validate_parameters_with_or(self):
        fake_1 = FakeWithStringIdFactory()
        fake_2 = FakeWithStringIdFactory()
        value = '{0}|{1}'.format(fake_1.id, fake_2.id)
        assert self.facet.validate_parameter(value)


class RangeFacetTest(FacetTestCase):
    def setUp(self):
        self.ranges = [
            ('first', (None, 1)),
            ('second', (1, 5)),
            ('third', (5, None))
        ]
        self.facet = search.RangeFacet(
            field='some_field',
            ranges=self.ranges,
            labels={
                'first': 'First range',
                'second': 'Second range',
                'third': 'Third range',
            })

    def buckets(self, first=1, second=2, third=3):
        return [{
            'to': 1.0,
            'to_as_string': '1.0',
            'key': 'first',
            'doc_count': first
        }, {
            'from': 1.0,
            'from_as_string': '1.0',
            'to_as_string': '5.0',
            'key': 'second',
            'doc_count': second
        }, {
            'from_as_string': '5.0',
            'from': 5.0, 'key':
            'third', 'doc_count': third
        }]

    def test_get_values(self):
        buckets = self.buckets()
        result = self.factory(aggregations=bucket_agg_factory(buckets))

        assert len(result) == len(self.ranges)
        assert result[0], ('first', 1 == False)
        assert result[1], ('second', 2 == False)
        assert result[2], ('third', 3 == False)

    def test_get_values_with_empty(self):
        buckets = self.buckets(second=0)
        result = self.factory(aggregations=bucket_agg_factory(buckets))

        assert len(result) == len(self.ranges) - 1
        assert result[0], ('first', 1 == False)
        assert result[1], ('third', 3 == False)

    def test_labelize(self):
        assert self.facet.labelize('first') == 'First range'

    def test_validate_parameters(self):
        for value in self.facet.labels.keys():
            assert self.facet.validate_parameter(value)

        bad_values = ['xyz', True, 45]
        for value in bad_values:
            with pytest.raises(Exception):
                self.facet.validate_parameter(value)

    def test_labels_ranges_mismatch(self):
        with pytest.raises(ValueError):
            search.RangeFacet(
                field='some_field',
                ranges=self.ranges,
                labels={
                    'first': 'First range',
                    'second': 'Second range',
                })
        with pytest.raises(ValueError):
            search.RangeFacet(
                field='some_field',
                ranges=self.ranges,
                labels={
                    'first': 'First range',
                    'second': 'Second range',
                    'unknown': 'Third range',
                })

    def test_get_value_filter(self):
        expected = Q({'range': {
            'some_field': {
                'gte': 1,
                'lt': 5,
            }
        }})
        assert self.facet.get_value_filter('second') == expected


class TemporalCoverageFacetTest(FacetTestCase):
    def setUp(self):
        self.facet = search.TemporalCoverageFacet(field='some_field')

    def test_get_aggregation(self):
        expected = A({
            'nested': {
                'path': 'some_field'
            },
            'aggs': {
                'min_start': {'min': {'field': 'some_field.start'}},
                'max_end': {'max': {'field': 'some_field.end'}}
            }
        })
        assert self.facet.get_aggregation() == expected

    def test_get_values(self):
        today = date.today()
        two_days_ago = today - timedelta(days=2, minutes=60)
        result = self.factory(aggregations={'test': {
            'min_start': {'value': float(two_days_ago.toordinal())},
            'max_end': {'value': float(today.toordinal())},
        }})
        assert result['min'] == two_days_ago
        assert result['max'] == today
        assert result['days'] == 2.0

    def test_value_filter(self):
        value_filter = self.facet.get_value_filter('2013-01-07-2014-06-07')
        q_start = Q({'range': {'some_field.start': {
            'lte': date(2014, 6, 7).toordinal(),
        }}})
        q_end = Q({'range': {'some_field.end': {
            'gte': date(2013, 1, 7).toordinal(),
        }}})
        expected = Q('nested', path='some_field', query=q_start & q_end)
        assert value_filter == expected

    def test_value_filter_reversed(self):
        value_filter = self.facet.get_value_filter('2014-06-07-2013-01-07')
        q_start = Q({'range': {'some_field.start': {
            'lte': date(2014, 6, 7).toordinal(),
        }}})
        q_end = Q({'range': {'some_field.end': {
            'gte': date(2013, 1, 7).toordinal(),
        }}})
        expected = Q('nested', path='some_field', query=q_start & q_end)
        assert value_filter == expected

    def test_labelize(self):
        label = self.facet.labelize('1940-01-01-2014-12-31')
        expected = '{0} - {1}'.format(
            format_date(date(1940, 1, 1), 'short'),
            format_date(date(2014, 12, 31), 'short')
        )
        assert label == expected

    def test_validate_parameters(self):
        value = '1940-01-01-2014-12-31'
        assert self.facet.validate_parameter(value) == value

        bad_values = ['xyz', True, 42]
        for value in bad_values:
            with pytest.raises(ValueError):
                self.facet.validate_parameter(value)
