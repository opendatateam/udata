from datetime import UTC, datetime

from flask import url_for

from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member
from udata.core.user.factories import UserFactory
from udata.core.visualizations.factories import ChartFactory, FilterFactory
from udata.core.visualizations.models import AndFilters, Chart

from . import PytestOnlyAPITestCase


class VisualizationAPITest(PytestOnlyAPITestCase):
    def test_visualization_api_list(self):
        """It should list visualizations"""
        ChartFactory()
        response = self.get(url_for("api.visualizations"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1

    def test_visualization_api_list_excludes_private(self):
        """It should not list private visualizations"""
        ChartFactory()
        ChartFactory(private=True)
        response = self.get(url_for("api.visualizations"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1

    def test_visualization_api_list_excludes_deleted(self):
        """It should not list deleted visualizations"""
        ChartFactory()
        ChartFactory(deleted_at=datetime.now(UTC))
        response = self.get(url_for("api.visualizations"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1

    def test_visualization_api_get(self):
        """It should fetch a visualization from the API"""
        visualization = ChartFactory()
        response = self.get(url_for("api.visualization", visualization=visualization))
        assert response.status_code == 200
        assert response.json["title"] == visualization.title

    def test_visualization_api_get_by_slug(self):
        """It should fetch a visualization by slug"""
        visualization = ChartFactory(title="My Test Visualization")
        response = self.get(url_for("api.visualization", visualization=visualization.slug))
        assert response.status_code == 200
        assert response.json["id"] == str(visualization.id)

    def test_visualization_api_get_deleted(self):
        """It should return 410 for deleted visualization"""
        visualization = ChartFactory(deleted_at=datetime.now(UTC))
        response = self.get(url_for("api.visualization", visualization=visualization))
        assert response.status_code == 410

    def test_visualization_api_get_deleted_but_authorized(self):
        """It should fetch deleted visualization if user is owner"""
        user = self.login()
        visualization = ChartFactory(deleted_at=datetime.now(UTC), owner=user)
        response = self.get(url_for("api.visualization", visualization=visualization))
        assert response.status_code == 200

    def test_visualization_api_get_private(self):
        """It should return 404 for private visualization"""
        visualization = ChartFactory(private=True)
        response = self.get(url_for("api.visualization", visualization=visualization))
        assert response.status_code == 404

    def test_visualization_api_get_private_but_authorized(self):
        """It should fetch private visualization if user is owner"""
        user = self.login()
        visualization = ChartFactory(owner=user, private=True)
        response = self.get(url_for("api.visualization", visualization=visualization))
        assert response.status_code == 200

    def test_visualization_api_create(self):
        """It should create a visualization"""
        user = self.login()
        chart = ChartFactory.build(owner=user)
        chart.owner = str(user.id)
        response = self.post(
            url_for("api.visualizations"),
            chart.to_dict(),
        )
        assert response.status_code == 201
        assert Chart.objects.count() == 1

        visualization = Chart.objects.first()
        assert visualization.title == chart.title
        assert visualization.description == chart.description
        assert visualization.owner == user

    def test_visualization_api_create_filter(self):
        """It should create a visualization"""
        user = self.login()
        filter = FilterFactory()
        chart = ChartFactory.build(owner=user, series__0__filters=filter)
        chart.owner = str(user.id)
        response = self.post(
            url_for("api.visualizations"),
            chart.to_dict(),
        )
        assert response.status_code == 201
        assert Chart.objects.count() == 1

        visualization = Chart.objects.first()
        assert visualization.title == chart.title
        assert visualization.description == chart.description
        assert visualization.owner == user
        assert visualization.series[0].filters == filter

        # GET should serialize the filter fields, not return an empty dict
        response = self.get(url_for("api.visualization", visualization=visualization))
        assert response.status_code == 200
        filters_data = response.json["series"][0]["filters"]
        assert filters_data["column"] == filter.column
        assert filters_data["condition"] == filter.condition
        assert filters_data["value"] == filter.value

    def test_visualization_api_create_and_filter(self):
        """It should create a visualization"""
        user = self.login()
        filters = AndFilters(filters=[FilterFactory(), FilterFactory()])
        chart = ChartFactory.build(owner=user, series__0__filters=filters)
        chart.owner = str(user.id)
        response = self.post(
            url_for("api.visualizations"),
            chart.to_dict(),
        )
        assert response.status_code == 201
        assert Chart.objects.count() == 1

        visualization = Chart.objects.first()
        print(visualization.series[0].filters)
        print(filters)
        assert visualization.title == chart.title
        assert visualization.description == chart.description
        assert visualization.owner == user
        assert visualization.series[0].filters == filters

    def test_visualization_api_create_for_org(self):
        """It should create a visualization for an organization"""
        user = self.login()
        org = OrganizationFactory()
        org.members.append(Member(user=user, role="admin"))
        org.save()
        chart = ChartFactory.build(organization=org)
        chart.organization = str(org.id)
        response = self.post(
            url_for("api.visualizations"),
            chart.to_dict(),
        )
        assert response.status_code == 201

        visualization = Chart.objects.first()
        assert visualization.organization == org

    def test_visualization_api_create_requires_auth(self):
        """It should require authentication to create"""
        response = self.post(
            url_for("api.visualizations"),
            {
                "title": "My Visualization",
                "description": "A test visualization",
            },
        )
        assert response.status_code == 401

    def test_visualization_api_update(self):
        """It should update a visualization"""
        user = self.login()
        visualization = ChartFactory(owner=user)

        response = self.patch(
            url_for("api.visualization", visualization=visualization),
            {"title": "Updated Title"},
        )
        assert response.status_code == 200
        assert response.json["title"] == "Updated Title"

    def test_visualization_api_update_requires_permission(self):
        """It should require permission to update"""
        self.login()
        other_user = UserFactory()
        visualization = ChartFactory(owner=other_user)

        response = self.patch(
            url_for("api.visualization", visualization=visualization),
            {"title": "Updated Title"},
        )
        assert response.status_code == 403

    def test_visualization_api_update_deleted(self):
        """It should return 410 when updating deleted visualization"""
        user = self.login()
        visualization = ChartFactory(owner=user, deleted_at=datetime.now(UTC))

        response = self.patch(
            url_for("api.visualization", visualization=visualization),
            {"title": "Updated Title"},
        )
        assert response.status_code == 410

    def test_visualization_api_delete(self):
        """It should soft delete a visualization"""
        user = self.login()
        visualization = ChartFactory(owner=user)

        response = self.delete(url_for("api.visualization", visualization=visualization))
        assert response.status_code == 204

        visualization.reload()
        assert visualization.deleted_at is not None

    def test_visualization_api_delete_requires_permission(self):
        """It should require permission to delete"""
        self.login()
        other_user = UserFactory()
        visualization = ChartFactory(owner=other_user)

        response = self.delete(url_for("api.visualization", visualization=visualization))
        assert response.status_code == 403

    def test_visualization_api_delete_already_deleted(self):
        """It should return 410 when deleting already deleted chart"""
        user = self.login()
        visualization = ChartFactory(owner=user, deleted_at=datetime.now(UTC))

        response = self.delete(url_for("api.visualization", visualization=visualization))
        assert response.status_code == 410


class ChartAPITest(PytestOnlyAPITestCase):
    def test_chart_api_get(self):
        """It should fetch a chart"""
        chart = ChartFactory()
        response = self.get(url_for("api.visualization", visualization=chart))
        assert response.status_code == 200
        assert response.json["title"] == chart.title
