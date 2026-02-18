from flask import url_for

from udata.auth import login_user
from udata.core.dataset.factories import DatasetFactory
from udata.core.organization.assignment import Assignment, clean_assignments_on_owner_change  # noqa
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member, MembershipRequest
from udata.core.user.factories import UserFactory
from udata.features.transfer.actions import accept_transfer
from udata.features.transfer.factories import TransferFactory
from udata.models import Dataset

from . import APITestCase


class PartialEditorDatasetAPITest(APITestCase):
    def setUp(self):
        super().setUp()
        self.admin_user = UserFactory()
        self.editor_user = UserFactory()
        self.partial_editor_user = UserFactory()

        self.org = OrganizationFactory(
            members=[
                Member(user=self.admin_user, role="admin"),
                Member(user=self.editor_user, role="editor"),
                Member(user=self.partial_editor_user, role="partial_editor"),
            ]
        )

        self.dataset_assigned = DatasetFactory(organization=self.org)
        self.dataset_other = DatasetFactory(organization=self.org)

    def assign_dataset_to_partial_editor(self):
        """Admin assigns dataset_assigned to the partial_editor via API."""
        self.login(self.admin_user)
        response = self.put(
            url_for(
                "api.member_assignments",
                org=self.org,
                user=self.partial_editor_user,
            ),
            [{"class": "Dataset", "id": str(self.dataset_assigned.id)}],
        )
        self.assert200(response)
        self.logout()
        return response

    def test_partial_editor_can_create_dataset_and_is_auto_assigned(self):
        """A partial_editor can create a dataset and gets auto-assigned to it."""
        self.login(self.partial_editor_user)
        data = DatasetFactory.as_dict()
        data["organization"] = str(self.org.id)
        response = self.post(url_for("api.datasets"), data)
        self.assert201(response)
        self.assertEqual(Dataset.objects.count(), 3)

        created_dataset = Dataset.objects.get(id=response.json["id"])
        self.assertTrue(
            Assignment.objects(user=self.partial_editor_user, subject=created_dataset).count() > 0
        )

        # Verify the partial editor can edit the dataset they just created
        data = created_dataset.to_dict()
        data["description"] = "updated after creation"
        response = self.put(url_for("api.dataset", dataset=created_dataset), data)
        self.assert200(response)

    def test_partial_editor_cannot_edit_unassigned_dataset(self):
        """A partial_editor cannot edit a dataset they are not assigned to."""
        self.login(self.partial_editor_user)
        data = self.dataset_other.to_dict()
        data["description"] = "hacked description"
        response = self.put(url_for("api.dataset", dataset=self.dataset_other), data)
        self.assert403(response)
        self.dataset_other.reload()
        self.assertNotEqual(self.dataset_other.description, "hacked description")

    def test_partial_editor_can_edit_assigned_dataset(self):
        """A partial_editor can edit a dataset they are assigned to."""
        self.assign_dataset_to_partial_editor()

        self.login(self.partial_editor_user)
        data = self.dataset_assigned.to_dict()
        data["description"] = "updated by partial editor"
        response = self.put(url_for("api.dataset", dataset=self.dataset_assigned), data)
        self.assert200(response)
        self.dataset_assigned.reload()
        self.assertEqual(self.dataset_assigned.description, "updated by partial editor")

    def test_partial_editor_still_cannot_edit_other_dataset_after_assignment(self):
        """After being assigned one dataset, partial_editor still can't edit other datasets."""
        self.assign_dataset_to_partial_editor()

        self.login(self.partial_editor_user)
        data = self.dataset_other.to_dict()
        data["description"] = "should not work"
        response = self.put(url_for("api.dataset", dataset=self.dataset_other), data)
        self.assert403(response)

    def test_editor_can_still_edit_all_datasets(self):
        """Regular editor can edit all datasets regardless of assignments."""
        self.login(self.editor_user)

        data = self.dataset_assigned.to_dict()
        data["description"] = "editor update 1"
        response = self.put(url_for("api.dataset", dataset=self.dataset_assigned), data)
        self.assert200(response)

        data = self.dataset_other.to_dict()
        data["description"] = "editor update 2"
        response = self.put(url_for("api.dataset", dataset=self.dataset_other), data)
        self.assert200(response)

    def test_admin_can_still_edit_all_datasets(self):
        """Admin can edit all datasets regardless of assignments."""
        self.login(self.admin_user)

        data = self.dataset_assigned.to_dict()
        data["description"] = "admin update 1"
        response = self.put(url_for("api.dataset", dataset=self.dataset_assigned), data)
        self.assert200(response)

        data = self.dataset_other.to_dict()
        data["description"] = "admin update 2"
        response = self.put(url_for("api.dataset", dataset=self.dataset_other), data)
        self.assert200(response)

    def test_admin_can_sync_assignments(self):
        """Admin can sync assignments for a partial_editor."""
        self.login(self.admin_user)
        url = url_for(
            "api.member_assignments",
            org=self.org,
            user=self.partial_editor_user,
        )

        # Assign one dataset
        response = self.put(url, [{"class": "Dataset", "id": str(self.dataset_assigned.id)}])
        self.assert200(response)
        self.assertEqual(len(response.json), 1)

        # List all org assignments
        response = self.get(url_for("api.organization_assignments", org=self.org))
        self.assert200(response)
        self.assertEqual(len(response.json), 1)

        # Sync with both datasets
        response = self.put(
            url,
            [
                {"class": "Dataset", "id": str(self.dataset_assigned.id)},
                {"class": "Dataset", "id": str(self.dataset_other.id)},
            ],
        )
        self.assert200(response)
        self.assertEqual(len(response.json), 2)

        # Sync with empty list (remove all)
        response = self.put(url, [])
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

        # Verify partial_editor can no longer edit
        self.login(self.partial_editor_user)
        data = self.dataset_assigned.to_dict()
        data["description"] = "should fail now"
        response = self.put(url_for("api.dataset", dataset=self.dataset_assigned), data)
        self.assert403(response)

    def test_editor_cannot_manage_assignments(self):
        """Only admins can manage assignments, not editors."""
        self.login(self.editor_user)
        response = self.put(
            url_for(
                "api.member_assignments",
                org=self.org,
                user=self.partial_editor_user,
            ),
            [{"class": "Dataset", "id": str(self.dataset_assigned.id)}],
        )
        self.assert403(response)

    def test_cannot_assign_object_from_another_org(self):
        """Cannot assign an object that doesn't belong to the organization."""
        other_org = OrganizationFactory()
        other_dataset = DatasetFactory(organization=other_org)

        self.login(self.admin_user)
        response = self.put(
            url_for(
                "api.member_assignments",
                org=self.org,
                user=self.partial_editor_user,
            ),
            [{"class": "Dataset", "id": str(other_dataset.id)}],
        )
        self.assert400(response)

    def test_cannot_assign_to_non_partial_editor(self):
        """Cannot assign objects to members who are not partial_editors."""
        self.login(self.admin_user)
        response = self.put(
            url_for(
                "api.member_assignments",
                org=self.org,
                user=self.editor_user,
            ),
            [{"class": "Dataset", "id": str(self.dataset_assigned.id)}],
        )
        self.assert400(response)

    def test_removing_member_cleans_up_assignments(self):
        """When a partial_editor is removed from the org, their assignments are deleted."""
        self.assign_dataset_to_partial_editor()

        self.login(self.admin_user)

        # Remove the partial_editor from the org
        response = self.delete(url_for("api.member", org=self.org, user=self.partial_editor_user))
        self.assert204(response)

        # Verify assignments are cleaned up
        response = self.get(url_for("api.organization_assignments", org=self.org))
        self.assert200(response)
        self.assertEqual(len(response.json), 0)


class PartialEditorInvitationAssignmentTest(APITestCase):
    def setUp(self):
        super().setUp()
        self.admin_user = UserFactory()
        self.org = OrganizationFactory(members=[Member(user=self.admin_user, role="admin")])
        self.dataset1 = DatasetFactory(organization=self.org)
        self.dataset2 = DatasetFactory(organization=self.org)

    def test_invite_partial_editor_with_assignments_then_accept(self):
        """Inviting a partial_editor with assignments creates assignments on acceptance."""
        invited_user = UserFactory()
        self.login(self.admin_user)
        response = self.post(
            url_for("api.invite_member", org=self.org),
            {
                "user": str(invited_user.id),
                "role": "partial_editor",
                "assignments": [
                    {"class": "Dataset", "id": str(self.dataset1.id)},
                    {"class": "Dataset", "id": str(self.dataset2.id)},
                ],
            },
        )
        self.assert201(response)
        self.assertEqual(len(response.json["assignments"]), 2)

        # Accept the invitation
        invitation_id = response.json["id"]
        self.login(invited_user)
        response = self.post(url_for("api.accept_org_invitation", id=invitation_id))
        self.assert200(response)

        # Verify assignments were created
        assignments = Assignment.objects(user=invited_user, organization=self.org)
        self.assertEqual(assignments.count(), 2)

        # Verify partial_editor can edit assigned datasets
        data = self.dataset1.to_dict()
        data["description"] = "updated by partial editor"
        response = self.put(url_for("api.dataset", dataset=self.dataset1), data)
        self.assert200(response)

    def test_invite_with_assignments_requires_partial_editor_role(self):
        """Assignments can only be set for partial_editor invitations."""
        invited_user = UserFactory()
        self.login(self.admin_user)
        response = self.post(
            url_for("api.invite_member", org=self.org),
            {
                "user": str(invited_user.id),
                "role": "editor",
                "assignments": [{"class": "Dataset", "id": str(self.dataset1.id)}],
            },
        )
        self.assert400(response)

    def test_invite_with_assignments_from_other_org(self):
        """Cannot assign objects from another organization."""
        invited_user = UserFactory()
        other_org = OrganizationFactory()
        other_dataset = DatasetFactory(organization=other_org)

        self.login(self.admin_user)
        response = self.post(
            url_for("api.invite_member", org=self.org),
            {
                "user": str(invited_user.id),
                "role": "partial_editor",
                "assignments": [{"class": "Dataset", "id": str(other_dataset.id)}],
            },
        )
        self.assert400(response)

    def test_invite_without_assignments_still_works(self):
        """Inviting a partial_editor without assignments works (assignments added later)."""
        invited_user = UserFactory()
        self.login(self.admin_user)
        response = self.post(
            url_for("api.invite_member", org=self.org),
            {
                "user": str(invited_user.id),
                "role": "partial_editor",
            },
        )
        self.assert201(response)
        self.assertEqual(len(response.json["assignments"]), 0)

    def test_list_invitations_includes_assignments(self):
        """Pending invitations listing includes assignments."""
        invited_user = UserFactory()
        invitation = MembershipRequest(
            kind="invitation",
            user=invited_user,
            created_by=self.admin_user,
            role="partial_editor",
            assignments=[self.dataset1, self.dataset2],
        )
        self.org.requests.append(invitation)
        self.org.save()

        self.login(invited_user)
        response = self.get(url_for("api.my_org_invitations"))
        self.assert200(response)
        self.assertEqual(len(response.json), 1)
        self.assertEqual(len(response.json[0]["assignments"]), 2)
        assignment_ids = {a["id"] for a in response.json[0]["assignments"]}
        self.assertIn(str(self.dataset1.id), assignment_ids)

    def test_accept_invitation_skips_deleted_subjects(self):
        """If a dataset is deleted between invitation and acceptance, the assignment is skipped."""
        invited_user = UserFactory()
        invitation = MembershipRequest(
            kind="invitation",
            user=invited_user,
            created_by=self.admin_user,
            role="partial_editor",
            assignments=[self.dataset1, self.dataset2],
        )
        self.org.requests.append(invitation)
        self.org.save()

        self.dataset1.delete()

        self.login(invited_user)
        response = self.post(url_for("api.accept_org_invitation", id=invitation.id))
        self.assert200(response)

        # Only dataset2 should have an assignment
        assignments = Assignment.objects(user=invited_user, organization=self.org)
        self.assertEqual(assignments.count(), 1)
        self.assertEqual(assignments.first().subject, self.dataset2)

    def test_accept_invitation_skips_transferred_subjects(self):
        """If a dataset is transferred to another org between invitation and acceptance,
        the assignment is skipped."""
        invited_user = UserFactory()
        invitation = MembershipRequest(
            kind="invitation",
            user=invited_user,
            created_by=self.admin_user,
            role="partial_editor",
            assignments=[self.dataset1, self.dataset2],
        )
        self.org.requests.append(invitation)
        self.org.save()

        other_org = OrganizationFactory()
        self.dataset1.organization = other_org
        self.dataset1.save()

        self.login(invited_user)
        response = self.post(url_for("api.accept_org_invitation", id=invitation.id))
        self.assert200(response)

        assignments = Assignment.objects(user=invited_user, organization=self.org)
        self.assertEqual(assignments.count(), 1)
        self.assertEqual(assignments.first().subject, self.dataset2)


class AssignmentIntegrityTest(APITestCase):
    """Tests for assignment cleanup on lifecycle events."""

    def setUp(self):
        super().setUp()
        self.admin_user = UserFactory()
        self.partial_editor = UserFactory()
        self.org = OrganizationFactory(
            members=[
                Member(user=self.admin_user, role="admin"),
                Member(user=self.partial_editor, role="partial_editor"),
            ]
        )
        self.dataset = DatasetFactory(organization=self.org)
        Assignment(
            user=self.partial_editor,
            organization=self.org,
            subject=self.dataset,
        ).save()

    def test_transfer_to_other_org_cleans_assignments(self):
        """When a dataset is transferred to another org, assignments are removed."""
        other_admin = UserFactory()
        other_org = OrganizationFactory(members=[Member(user=other_admin, role="admin")])
        transfer = TransferFactory(owner=self.org, recipient=other_org, subject=self.dataset)

        login_user(other_admin)
        accept_transfer(transfer)

        self.assertEqual(Assignment.objects(subject=self.dataset).count(), 0)

    def test_transfer_to_user_cleans_assignments(self):
        """When a dataset is transferred to a user, assignments are removed."""
        recipient = UserFactory()
        transfer = TransferFactory(owner=self.org, recipient=recipient, subject=self.dataset)

        login_user(recipient)
        accept_transfer(transfer)

        self.assertEqual(Assignment.objects(subject=self.dataset).count(), 0)

    def test_role_change_from_partial_editor_cleans_assignments(self):
        """When a partial_editor is promoted to editor, their assignments are removed."""
        self.assertEqual(
            Assignment.objects(user=self.partial_editor, organization=self.org).count(), 1
        )

        self.login(self.admin_user)
        response = self.put(
            url_for("api.member", org=self.org, user=self.partial_editor),
            {"role": "editor"},
        )
        self.assert200(response)

        self.assertEqual(
            Assignment.objects(user=self.partial_editor, organization=self.org).count(), 0
        )

    def test_role_change_to_partial_editor_keeps_no_assignments(self):
        """When an editor becomes partial_editor, they start with no assignments."""
        editor = UserFactory()
        self.org.members.append(Member(user=editor, role="editor"))
        self.org.save()

        self.login(self.admin_user)
        response = self.put(
            url_for("api.member", org=self.org, user=editor),
            {"role": "partial_editor"},
        )
        self.assert200(response)

        self.assertEqual(Assignment.objects(user=editor, organization=self.org).count(), 0)
