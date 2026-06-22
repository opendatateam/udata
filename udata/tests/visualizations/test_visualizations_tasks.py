from datetime import datetime
from unittest.mock import MagicMock, patch

from pytz import UTC

from udata.core.user.factories import UserFactory
from udata.core.visualizations.factories import ChartFactory
from udata.core.visualizations.models import Chart
from udata.core.visualizations.tasks import purge_visualizations
from udata.tests.api import PytestOnlyDBTestCase


class VisualizationTasksTest(PytestOnlyDBTestCase):
    def test_purge_visualization_with_image(self):
        """It should purge a deleted visualization and its image files"""
        from udata.core.visualizations import tasks

        user = UserFactory()
        chart = ChartFactory(owner=user)
        chart.deleted_at = datetime.now(UTC)
        chart.save()
        chart_id = chart.id

        tasks.purge_visualizations()

        # Chart should be deleted
        assert Chart.objects.filter(id=chart_id).count() == 0

    def test_purge_visualization_without_image(self):
        """It should purge a deleted visualization without image files"""
        user = UserFactory()
        chart = ChartFactory(owner=user, image=None)
        chart.deleted_at = datetime.now(UTC)
        chart.save()

        mock_storage = MagicMock()

        with patch("udata.core.visualizations.tasks.storages.images", mock_storage):
            with patch.object(Chart, "objects") as mock_query:
                mock_query.return_value = [chart]
                purge_visualizations()

        assert mock_storage.delete.call_count == 0

    def test_purge_no_deleted_visualizations(self):
        """It should handle no deleted visualizations gracefully"""
        mock_storage = MagicMock()

        with patch("udata.core.visualizations.tasks.storages.images", mock_storage):
            with patch.object(Chart, "objects") as mock_query:
                mock_query.return_value = []
                purge_visualizations()

        assert mock_storage.delete.call_count == 0
