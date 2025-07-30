import pytest

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import CommunityResourceFactory, DatasetFactory, ResourceFactory
from udata.core.metrics.tasks import (
    iterate_on_metrics,
    update_dataservices,
    update_datasets,
    update_organizations,
    update_resources_and_community_resources,
    update_reuses,
)
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory

from .helpers import mock_metrics_api


def test_iterate_on_metrics(app, rmock):
    mock_metrics_api(
        app,
        rmock,
        "test_model",
        ["test_key", "second_key"],
        [
            {"id": 123},
            {"id": 42},
            {"id": 1337},
        ],
        page_size=2,
    )

    metrics_data = list(iterate_on_metrics("test_model", ["test_key", "second_key"], page_size=2))

    assert metrics_data == [
        {"__id": 0, "id": 123},
        {"__id": 1, "id": 42},
        {"__id": 2, "id": 1337},
    ]


@pytest.mark.parametrize(
    "endpoint,id_key,factory,func,api_key",
    [
        ("dataservices", "dataservice_id", DataserviceFactory, update_dataservices, "visit"),
        ("reuses", "reuse_id", ReuseFactory, update_reuses, "visit"),
        (
            "organizations",
            "organization_id",
            OrganizationFactory,
            update_organizations,
            "visit_dataset",
        ),
    ],
)
def test_update_simple_visit_to_views_metrics(app, rmock, endpoint, id_key, factory, func, api_key):
    models = [factory() for i in range(15)]
    mock_metrics_api(
        app,
        rmock,
        endpoint,
        [api_key],
        [
            {id_key: str(models[1].id), api_key: 42},
            {id_key: str(models[3].id), api_key: 1337},
            {id_key: str(models[4].id), api_key: 2},
        ],
    )

    func()
    [model.reload() for model in models]

    assert models[1].metrics.get("views") == 42
    assert models[3].metrics.get("views") == 1337
    assert models[4].metrics.get("views") == 2


def test_update_datasets(app, rmock):
    datasets = [DatasetFactory() for i in range(15)]
    mock_metrics_api(
        app,
        rmock,
        "datasets",
        ["visit", "download_resource"],
        [
            {"dataset_id": str(datasets[1].id), "visit": 42, "download_resource": 123},
            {"dataset_id": str(datasets[3].id), "visit": 1337, "download_resource": 4242},
            {"dataset_id": str(datasets[4].id), "visit": 2, "download_resource": 7},
        ],
    )

    update_datasets()
    [model.reload() for model in datasets]

    assert datasets[1].metrics.get("views") == 42
    assert datasets[1].metrics.get("resources_downloads") == 123
    assert datasets[3].metrics.get("views") == 1337
    assert datasets[3].metrics.get("resources_downloads") == 4242
    assert datasets[4].metrics.get("views") == 2
    assert datasets[4].metrics.get("resources_downloads") == 7


def test_update_resources_metrics(app, rmock):
    resources = [ResourceFactory() for i in range(5)]
    dataset_a_with_resources = DatasetFactory(resources=resources)
    dataset_b_with_resource = DatasetFactory(resources=[ResourceFactory()])

    community_resources = [CommunityResourceFactory() for i in range(10)]

    dataset_without_resource = DatasetFactory()

    mock_metrics_api(
        app,
        rmock,
        "resources",
        ["download_resource"],
        [
            {
                "resource_id": str(dataset_a_with_resources.resources[0].id),
                "dataset_id": str(dataset_a_with_resources.id),
                "download_resource": 42,
            },
            {
                "resource_id": str(community_resources[3].id),
                "dataset_id": None,
                "download_resource": 16,
            },
            {
                "resource_id": str(community_resources[5].id),
                "dataset_id": None,
                "download_resource": 111,
            },
            {
                "resource_id": str(dataset_a_with_resources.resources[1].id),
                "dataset_id": str(dataset_a_with_resources.id),
                "download_resource": 1337,
            },
            {
                "resource_id": str(dataset_b_with_resource.resources[0].id),
                "dataset_id": str(dataset_b_with_resource.id),
                "download_resource": 1404,
            },
            {
                "resource_id": str(dataset_a_with_resources.resources[4].id),
                "dataset_id": str(dataset_a_with_resources.id),
                "download_resource": 2,
            },
            {
                "resource_id": str(community_resources[9].id),
                "dataset_id": None,
                "download_resource": 1,
            },
        ],
    )

    update_resources_and_community_resources()

    dataset_a_with_resources.reload()
    dataset_b_with_resource.reload()
    dataset_without_resource.reload()
    [community_resource.reload() for community_resource in community_resources]

    assert community_resources[3].metrics.get("views") == 16
    assert community_resources[5].metrics.get("views") == 111
    assert community_resources[9].metrics.get("views") == 1

    assert dataset_a_with_resources.resources[0].metrics.get("views") == 42
    assert dataset_a_with_resources.resources[1].metrics.get("views") == 1337
    assert dataset_a_with_resources.resources[4].metrics.get("views") == 2

    assert dataset_b_with_resource.resources[0].metrics.get("views") == 1404
