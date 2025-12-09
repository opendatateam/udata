import pytest

from udata.core.dataset.factories import ResourceFactory
from udata.tests.api import PytestOnlyAPITestCase

DUMMY_EXTRAS = {
    "analysis:parsing:finished_at": "1987-12-23T10:55:00.000000+00:00",
    "analysis:parsing:parsing_table": "xxx",
}
MAX_SIZE = 50000


class ResourcePreviewTest(PytestOnlyAPITestCase):
    def expected_url(self, rid):
        return "http://preview.me/resources/{0}".format(rid)

    @pytest.mark.options(TABULAR_EXPLORE_URL="http://preview.me")
    def test_display_preview_for_tabular_resources(self):
        resource = ResourceFactory(extras=DUMMY_EXTRAS)
        assert resource.preview_url == self.expected_url(resource.id)

    @pytest.mark.options(TABULAR_EXPLORE_URL=None)
    def test_no_preview_if_no_conf(self):
        assert ResourceFactory(extras=DUMMY_EXTRAS).preview_url is None

    @pytest.mark.options(TABULAR_EXPLORE_URL="http://preview.me")
    def test_default_allow_remote_preview(self):
        resources = [
            ResourceFactory(extras=DUMMY_EXTRAS),
            ResourceFactory(filetype="remote", extras=DUMMY_EXTRAS),
        ]

        for resource in resources:
            assert resource.preview_url == self.expected_url(resource.id)

    @pytest.mark.options(
        TABULAR_EXPLORE_URL="http://preview.me",
        TABULAR_ALLOW_REMOTE=False,
    )
    def test_allow_remote_preview_false(self):
        local = ResourceFactory(extras=DUMMY_EXTRAS)
        remote = ResourceFactory(filetype="remote", extras=DUMMY_EXTRAS)

        assert local.preview_url == self.expected_url(local.id)
        assert remote.preview_url is None

    @pytest.mark.options(TABULAR_EXPLORE_URL="http://preview.me")
    def test_display_preview_without_max_size(self):
        resource = ResourceFactory(extras=DUMMY_EXTRAS, filesize=2 * MAX_SIZE)

        assert resource.preview_url == self.expected_url(resource.id)

    @pytest.mark.options(TABULAR_EXPLORE_URL="http://preview.me")
    def test_no_preview_if_no_parsing_table_info(self):
        extras = DUMMY_EXTRAS
        del extras["analysis:parsing:parsing_table"]

        resource = ResourceFactory(extras=extras, filesize=2 * MAX_SIZE)
        assert resource.preview_url is None
