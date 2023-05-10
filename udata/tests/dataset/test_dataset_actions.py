import pytest

from udata.core.dataset.actions import archive
from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.discussions.models import Discussion
from udata.core.user.factories import UserFactory


@pytest.mark.usefixtures('clean_db')
class DatasetActionsTest:

    def test_dataset_archive(self, app):
        user = UserFactory()
        app.config['ARCHIVE_COMMENT_USER_ID'] = user.id

        dataset = VisibleDatasetFactory()

        archive(dataset, comment=True)

        dataset.reload()
        assert dataset.archived is not None
        discussions = Discussion.objects.filter(subject=dataset)
        assert len(discussions) == 1
        assert discussions[0].discussion[0].posted_by == user
