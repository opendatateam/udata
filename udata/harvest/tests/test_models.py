import logging
import pytest

from udata.utils import faker

from ..models import HarvestSource


log = logging.getLogger(__name__)


@pytest.mark.usefixtures('clean_db')
class HarvestSourceTest:
    def test_defaults(self):
        source = HarvestSource.objects.create(name='Test', url=faker.url(), backend='factory')
        assert source.name == 'Test'
        assert source.slug == 'test'

    def test_domain(self):
        source = HarvestSource(name='Test',
                               url='http://www.somewhere.com/path/')
        assert source.domain == 'www.somewhere.com'

        source = HarvestSource(name='Test',
                               url='https://www.somewhere.com/path/')
        assert source.domain == 'www.somewhere.com'

        source = HarvestSource(name='Test',
                               url='http://www.somewhere.com:666/path/')
        assert source.domain == 'www.somewhere.com'
