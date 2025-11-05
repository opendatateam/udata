import udata.core.dataservices.tasks  # noqa
import udata.core.dataset.tasks  # noqa
from udata.core.badges.tasks import update_badges
from udata.core.constants import HVD
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.models import Dataset
from udata.core.organization.constants import CERTIFIED, PUBLIC_SERVICE
from udata.core.organization.factories import OrganizationFactory
from udata.tests.api import DBTestCase


class BadgeTasksTest(DBTestCase):
    def test_update_badges(self):
        """
        Test update_badges run the appropriate badge update jobs.
        In particular, test that the two following registered jobs run and work as expected:
        - update_dataset_hvd_badge
        - update_dataservice_hvd_badge
        """
        org = OrganizationFactory()
        org.add_badge(PUBLIC_SERVICE)
        org.add_badge(CERTIFIED)

        datasets = [
            DatasetFactory(organization=org, tags=["hvd"]),  # Should be badged HVD
            DatasetFactory(organization=org, tags=["random"]),  # Should not be badged HVD
            DatasetFactory(
                organization=org,
                tags=[],
                badges=[Dataset.badges.field.document_type(kind=HVD)],
            ),  # Badge should be remove
        ]
        dataservices = [
            DataserviceFactory(organization=org, tags=["hvd"]),  # Should be badged HVD
            DataserviceFactory(organization=org, tags=["random"]),  # Should not be badged HVD
            DataserviceFactory(
                organization=org,
                tags=[],
                badges=[Dataservice.badges.field.document_type(kind=HVD)],
            ),  # Badge should be remove
        ]

        update_badges.run()

        [model.reload() for model in (*datasets, *dataservices)]

        assert datasets[0].badges[0].kind == HVD
        assert datasets[1].badges == []
        assert datasets[2].badges == []

        assert dataservices[0].badges[0].kind == HVD
        assert dataservices[1].badges == []
        assert dataservices[2].badges == []
