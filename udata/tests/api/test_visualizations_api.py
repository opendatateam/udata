from datetime import datetime

from flask import url_for

from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member
from udata.core.user.factories import UserFactory
from udata.core.visualizations.factories import ChartFactory
from udata.core.visualizations.models import Chart

from . import APITestCase


class VisualizationAPITest(APITestCase):
    def test_visualization_api_list(self):
        """It should list visualizations"""
        response = self.get(url_for("api.visualizations"))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), 3)

    def test_visualization_api_list_excludes_private(self):
        """It should not list private visualizations"""
        ChartFactory()
        ChartFactory(private=True)
        response = self.get(url_for("api.visualizations"))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), 1)

    def test_visualization_api_list_excludes_deleted(self):
        """It should not list deleted visualizations"""
        ChartFactory()
        ChartFactory(deleted_at=datetime.utcnow())
        response = self.get(url_for("api.visualizations"))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), 1)

    def test_visualization_api_get(self):
        """It should fetch a visualization from the API"""
        visualization = ChartFactory()
        response = self.get(url_for("api.visualization", visualization=visualization))
        self.assert200(response)
        self.assertEqual(response.json["title"], visualization.title)

    def test_visualization_api_get_by_slug(self):
        """It should fetch a visualization by slug"""
        visualization = ChartFactory(title="My Test Visualization")
        response = self.get(url_for("api.visualization", visualization=visualization.slug))
        self.assert200(response)
        self.assertEqual(response.json["id"], str(visualization.id))

    def test_visualization_api_get_deleted(self):
        """It should return 410 for deleted visualization"""
        visualization = ChartFactory(deleted_at=datetime.utcnow())
        response = self.get(url_for("api.visualization", visualization=visualization))
        self.assert410(response)

    def test_visualization_api_get_deleted_but_authorized(self):
        """It should fetch deleted visualization if user is owner"""
        user = self.login()
        visualization = ChartFactory(deleted_at=datetime.utcnow(), owner=user)
        response = self.get(url_for("api.visualization", visualization=visualization))
        self.assert200(response)

    def test_visualization_api_get_private(self):
        """It should return 404 for private visualization"""
        visualization = ChartFactory(private=True)
        response = self.get(url_for("api.visualization", visualization=visualization))
        self.assert404(response)

    def test_visualization_api_get_private_but_authorized(self):
        """It should fetch private visualization if user is owner"""
        user = self.login()
        visualization = ChartFactory(owner=user, private=True)
        response = self.get(url_for("api.visualization", visualization=visualization))
        self.assert200(response)

    def test_visualization_api_create(self):
        """It should create a visualization"""
        user = self.login()
        response = self.post(
            url_for("api.visualizations"),
            {
                "title": "My Visualization",
                "description": "A test visualization",
            },
        )
        self.assert201(response)
        self.assertEqual(Chart.objects.count(), 1)

        visualization = Chart.objects.first()
        self.assertEqual(visualization.title, "My Visualization")
        self.assertEqual(visualization.owner, user)

    def test_visualization_api_create_for_org(self):
        """It should create a visualization for an organization"""
        user = self.login()
        org = OrganizationFactory()
        org.members.append(Member(user=user, role="admin"))
        org.save()

        response = self.post(
            url_for("api.visualizations"),
            {
                "title": "Org Visualization",
                "description": "A test visualization",
                "organization": str(org.id),
            },
        )
        self.assert201(response)

        visualization = Chart.objects.first()
        self.assertEqual(visualization.organization, org)

    def test_visualization_api_create_requires_auth(self):
        """It should require authentication to create"""
        response = self.post(
            url_for("api.visualizations"),
            {
                "title": "My Visualization",
                "description": "A test visualization",
            },
        )
        self.assert401(response)

    def test_visualization_api_update(self):
        """It should update a visualization"""
        user = self.login()
        visualization = ChartFactory(owner=user)

        response = self.patch(
            url_for("api.visualization", visualization=visualization),
            {"title": "Updated Title"},
        )
        self.assert200(response)
        self.assertEqual(response.json["title"], "Updated Title")

    def test_visualization_api_update_requires_permission(self):
        """It should require permission to update"""
        self.login()
        other_user = UserFactory()
        visualization = ChartFactory(owner=other_user)

        response = self.patch(
            url_for("api.visualization", visualization=visualization),
            {"title": "Updated Title"},
        )
        self.assert403(response)

    def test_visualization_api_update_deleted(self):
        """It should return 410 when updating deleted visualization"""
        user = self.login()
        visualization = ChartFactory(owner=user, deleted_at=datetime.utcnow())

        response = self.patch(
            url_for("api.visualization", visualization=visualization),
            {"title": "Updated Title"},
        )
        self.assert410(response)

    def test_visualization_api_delete(self):
        """It should soft delete a visualization"""
        user = self.login()
        visualization = ChartFactory(owner=user)

        response = self.delete(url_for("api.visualization", visualization=visualization))
        self.assert204(response)

        visualization.reload()
        self.assertIsNotNone(visualization.deleted_at)

    def test_visualization_api_delete_requires_permission(self):
        """It should require permission to delete"""
        self.login()
        other_user = UserFactory()
        visualization = ChartFactory(owner=other_user)

        response = self.delete(url_for("api.visualization", visualization=visualization))
        self.assert403(response)

    def test_visualization_api_delete_already_deleted(self):
        """It should return 410 when deleting already deleted visualization"""
        user = self.login()
        visualization = ChartFactory(owner=user, deleted_at=datetime.utcnow())

        response = self.delete(url_for("api.visualization", visualization=visualization))
        self.assert410(response)


class ChartAPITest(APITestCase):
    def test_chart_api_get(self):
        """It should fetch a chart (subclass of visualization)"""
        chart = ChartFactory()
        response = self.get(url_for("api.visualization", visualization=chart))
        self.assert200(response)
        self.assertEqual(response.json["title"], chart.title)
