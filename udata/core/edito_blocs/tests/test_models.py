from uuid import uuid4

import pytest

from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.edito_blocs.models import check_resource_exists
from udata.mongo.errors import FieldValidationError
from udata.tests.api import PytestOnlyDBTestCase


class CheckResourceExistsTest(PytestOnlyDBTestCase):
    def test_existing_resource(self):
        resource = ResourceFactory()
        DatasetFactory(resources=[resource])

        check_resource_exists(str(resource.id), field="resource_id")

    def test_unknown_resource(self):
        with pytest.raises(FieldValidationError, match="Unknown resource"):
            check_resource_exists(str(uuid4()), field="resource_id")

    def test_invalid_uuid(self):
        with pytest.raises(FieldValidationError, match="not a valid UUID"):
            check_resource_exists("not-a-uuid", field="resource_id")
