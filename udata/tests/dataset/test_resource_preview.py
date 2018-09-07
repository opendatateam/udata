# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from udata.core.dataset.preview import PreviewPlugin, PreviewWarning
from udata.core.dataset.factories import DatasetFactory

pytestmark = [
    pytest.mark.usefixtures('clean_db')
]

PREVIEW_URL = 'http://preview'
FALLBACK_PREVIEW_URL = 'http://preview/default'


class AlwaysPreview(PreviewPlugin):
    def can_preview(self, resource):
        return True

    def preview_url(self, resource):
        return PREVIEW_URL


class NeverPreview(PreviewPlugin):
    def can_preview(self, resource):
        return False

    def preview_url(self, resource):
        return PREVIEW_URL


class PreviewFromDataset(PreviewPlugin):
    def can_preview(self, resource):
        return True

    def preview_url(self, resource):
        return resource.dataset.extras['preview']


class FallbackPreview(PreviewPlugin):
    fallback = True

    def can_preview(self, resource):
        return True

    def preview_url(self, resource):
        return FALLBACK_PREVIEW_URL


class NotAValidPlugin(object):
    fallback = False

    def can_preview(self, resource):
        return True

    def preview_url(self, resource):
        return PREVIEW_URL


class ResourcePreviewTest:
    @pytest.fixture(autouse=True)
    def patch_entrypoint(self, request, mocker, app):
        marker = request.node.get_closest_marker('preview')
        plugins = marker.args[0] if marker else []
        m = mocker.patch('udata.entrypoints.get_enabled')
        m.return_value.values.return_value = plugins  # Keep order
        yield
        m.assert_called_with('udata.preview', app)

    def test_preview_is_none_by_default(self):
        dataset = DatasetFactory(visible=True)
        resource = dataset.resources[0]
        assert resource.preview_url is None

    @pytest.mark.preview([NeverPreview])
    def test_resource_has_no_preview(self):
        dataset = DatasetFactory(visible=True)
        resource = dataset.resources[0]
        assert resource.preview_url is None

    @pytest.mark.preview([AlwaysPreview])
    def test_resource_has_preview(self):
        dataset = DatasetFactory(visible=True)
        resource = dataset.resources[0]
        assert resource.preview_url == PREVIEW_URL

    @pytest.mark.preview([AlwaysPreview, NeverPreview, NeverPreview])
    def test_resource_has_one_preview_with_multiple_plugins(self):
        dataset = DatasetFactory(visible=True)
        resource = dataset.resources[0]
        assert resource.preview_url == PREVIEW_URL

    @pytest.mark.preview([PreviewFromDataset])
    def test_can_access_dataset_metadata(self):
        dataset = DatasetFactory(visible=True,
                                 extras={'preview': PREVIEW_URL})
        resource = dataset.resources[0]
        assert resource.preview_url == PREVIEW_URL

    @pytest.mark.preview([AlwaysPreview, AlwaysPreview])
    def test_can_have_multiple_candidates(self):
        dataset = DatasetFactory(visible=True)
        resource = dataset.resources[0]
        assert resource.preview_url == PREVIEW_URL

    # order matters to ensure test is failing
    @pytest.mark.preview([NeverPreview, FallbackPreview, AlwaysPreview])
    def test_fallback_preview_comes_after(self):
        dataset = DatasetFactory(visible=True)
        resource = dataset.resources[0]
        assert resource.preview_url == PREVIEW_URL

    @pytest.mark.preview([NeverPreview, FallbackPreview])
    def test_fallback_on_default_preview(self):
        dataset = DatasetFactory(visible=True)
        resource = dataset.resources[0]
        assert resource.preview_url == FALLBACK_PREVIEW_URL

    @pytest.mark.preview([NotAValidPlugin])
    def test_warn_but_ignore_invalid_plugins(self):
        expected_msg = 'NotAValidPlugin is not a valid preview plugin'
        with pytest.warns(PreviewWarning, match=expected_msg):
            dataset = DatasetFactory(visible=True)
            resource = dataset.resources[0]
            assert resource.preview_url is None
