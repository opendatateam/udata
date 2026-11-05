from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

from flask import url_for

from udata.core import storages
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member
from udata.core.user.factories import UserFactory
from udata.core.visualizations.factories import ChartFactory
from udata.core.visualizations.models import Chart
from udata.tests.helpers import create_test_image

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

    def test_visualization_api_list_includes_own_private(self):
        """It should list private visualizations owned by the authenticated user"""
        user = self.login()
        ChartFactory()
        ChartFactory(owner=user, private=True)
        response = self.get(url_for("api.visualizations"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 2

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

    def test_visualization_api_create_with_query(self):
        """It should create a visualization with a SQL query and resource_id"""
        self.login()
        data = {
            "title": "My chart",
            "description": "Some description",
            "query": "SELECT region, COUNT(*) FROM data GROUP BY region",
            "resource_id": str(uuid4()),
        }
        response = self.post(url_for("api.visualizations"), data)
        assert response.status_code == 201
        assert response.json["query"] == data["query"]
        assert response.json["resource_id"] == data["resource_id"]

    def test_visualization_api_create_with_chart_type(self):
        """It should create a visualization with an explicit chart type"""
        self.login()
        data = {
            "title": "My chart",
            "description": "Some description",
            "query": "SELECT region, COUNT(*) FROM data GROUP BY region",
            "resource_id": str(uuid4()),
            "chart_type": "histogram",
        }
        response = self.post(url_for("api.visualizations"), data)
        assert response.status_code == 201
        assert response.json["chart_type"] == "histogram"

    def test_visualization_api_create_defaults_to_line_chart_type(self):
        """It should default to line chart type when none is provided"""
        self.login()
        data = {
            "title": "My chart",
            "description": "Some description",
            "query": "SELECT region, COUNT(*) FROM data GROUP BY region",
            "resource_id": str(uuid4()),
        }
        response = self.post(url_for("api.visualizations"), data)
        assert response.status_code == 201
        assert response.json["chart_type"] == "line"

    def test_visualization_api_create_invalid_chart_type(self):
        """It should not create a visualization with an invalid chart type"""
        self.login()
        data = {
            "title": "My chart",
            "description": "Some description",
            "query": "SELECT region, COUNT(*) FROM data GROUP BY region",
            "resource_id": str(uuid4()),
            "chart_type": "pie",
        }
        response = self.post(url_for("api.visualizations"), data)
        assert response.status_code == 400

    def test_visualization_api_create_without_query(self):
        """It should not create a visualization without a query"""
        self.login()
        data = {"title": "My chart", "description": "Some description", "resource_id": str(uuid4())}
        response = self.post(url_for("api.visualizations"), data)
        assert response.status_code == 400

    def test_visualization_api_create_rejects_non_read_only_query(self):
        """It should not create a visualization with a query that is not
        guaranteed to be a single read-only statement"""
        self.login()
        for query in (
            "DROP TABLE data",
            "SELECT a FROM data; DELETE FROM data",
            "SELECT read_csv('/etc/passwd')",
            "SELECT set_config('x', 'y', false)",
            "SELECT * INTO newtab FROM data",
        ):
            data = {
                "title": "My chart",
                "description": "Some description",
                "query": query,
                "resource_id": str(uuid4()),
            }
            response = self.post(url_for("api.visualizations"), data)
            assert response.status_code == 400, query
            assert Chart.objects.count() == 0

    def test_visualization_api_create_accepts_read_only_query(self):
        """It should create a visualization with a read-only query, CTEs included"""
        self.login()
        data = {
            "title": "My chart",
            "description": "Some description",
            "query": "WITH x AS (SELECT category, COUNT(*) AS n FROM data GROUP BY category) "
            "SELECT * FROM x ORDER BY n DESC",
            "resource_id": str(uuid4()),
        }
        response = self.post(url_for("api.visualizations"), data)
        assert response.status_code == 201

    def test_visualization_api_create_invalid_resource_id(self):
        """It should not create a visualization with an invalid resource_id"""
        self.login()
        data = {
            "title": "My chart",
            "description": "Some description",
            "query": "SELECT 1",
            "resource_id": "not-a-uuid",
        }
        response = self.post(url_for("api.visualizations"), data)
        assert response.status_code == 400

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

    def test_visualization_api_create_assigns_current_user_as_owner(self):
        """It should assign current user as owner when no owner or org is provided"""
        user = self.login()
        chart = ChartFactory.build()
        data = chart.to_dict()
        data.pop("owner", None)
        data.pop("organization", None)
        response = self.post(url_for("api.visualizations"), data)
        assert response.status_code == 201

        visualization = Chart.objects.first()
        assert visualization.owner == user

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

    def test_visualization_api_update_as_org_editor(self):
        """It should allow an org editor to update an org-owned visualization"""
        user = self.login()
        org = OrganizationFactory(members=[Member(user=user, role="editor")])
        visualization = ChartFactory(organization=org)

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


class VisualizationImageAPITest(PytestOnlyAPITestCase):
    def test_upload_image_success(self):
        """It should upload an image to a visualization"""
        user = self.login()
        visualization = ChartFactory(owner=user)
        file = create_test_image()

        response = self.post(
            url_for("api.visualization_image", visualization=visualization),
            {"file": (file, "test.png")},
            json=False,
        )
        assert response.status_code == 200
        assert response.json["image"] is not None

    def test_upload_image_replaces_previous_files(self):
        """Re-uploading an image should delete the files it replaces"""
        user = self.login()
        visualization = ChartFactory(owner=user)

        def upload():
            return self.post(
                url_for("api.visualization_image", visualization=visualization),
                {"file": (create_test_image(), "test.png")},
                json=False,
            )

        assert upload().status_code == 200
        visualization.reload()
        previous = {visualization.image.filename, visualization.image.original}

        assert upload().status_code == 200
        visualization.reload()
        current = {visualization.image.filename, visualization.image.original}

        assert not previous & current, "the re-upload should store new files"
        assert not any(filename in storages.images for filename in previous), (
            "the replaced files should be removed from storage"
        )
        assert all(filename in storages.images for filename in current)

    def test_upload_image_permission_denied(self):
        """It should deny upload for non-owner"""
        self.login()
        other_user = UserFactory()
        visualization = ChartFactory(owner=other_user)
        file = create_test_image()

        response = self.post(
            url_for("api.visualization_image", visualization=visualization),
            {"file": (file, "test.png")},
            json=False,
        )
        assert response.status_code == 403

    def test_upload_image_invalid_format(self):
        """It should reject non-image files"""
        user = self.login()
        visualization = ChartFactory(owner=user)

        response = self.post(
            url_for("api.visualization_image", visualization=visualization),
            {"file": (BytesIO(b"not an image"), "test.txt")},
            json=False,
        )
        assert response.status_code == 400
