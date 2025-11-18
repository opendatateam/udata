from datetime import datetime
from io import StringIO

import pytest
from flask import url_for

import udata.core.organization.constants as org_constants
from udata.core import csv
from udata.core.badges.factories import badge_factory
from udata.core.badges.signals import on_badge_added, on_badge_removed
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.discussions.factories import DiscussionFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.i18n import _
from udata.models import Discussion, Follow, Member, MembershipRequest, Organization
from udata.tests.api import PytestOnlyAPITestCase
from udata.tests.helpers import (
    assert200,
    assert201,
    assert204,
    assert400,
    assert403,
    assert404,
    assert410,
    assert_emit,
    assert_not_emit,
    assert_starts_with,
    assert_status,
)
from udata.utils import faker


class OrganizationAPITest(PytestOnlyAPITestCase):
    def test_organization_api_list(self):
        """It should fetch an organization list from the API"""
        organizations = OrganizationFactory.create_batch(3)

        response = self.get(url_for("api.organizations"))
        assert200(response)
        len(response.json["data"]) == len(organizations)

    def test_organization_api_list_with_filters(self):
        """It should filter the organization list"""
        org = OrganizationFactory(business_number_id="13002526500013")
        org_public_service = OrganizationFactory()
        org_public_service.add_badge(org_constants.PUBLIC_SERVICE)

        #### Badges ####
        response = self.get(url_for("api.organizations", badge=org_constants.PUBLIC_SERVICE))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(org_public_service.id)

        response = self.get(url_for("api.organizations", badge="bad-badge"))
        assert400(response)

        #### Name ####
        response = self.get(url_for("api.organizations", name=org.name))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(org.id)

        response = self.get(url_for("api.organizations", name=org.name.upper()))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(org.id)

        response = self.get(url_for("api.organizations", name="Some other name"))
        assert200(response)
        assert len(response.json["data"]) == 0

        #### SIRET ####
        response = self.get(url_for("api.organizations", business_number_id=org.business_number_id))
        assert200(response)
        print(response.json["data"])
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(org.id)

        response = self.get(url_for("api.organizations", business_number_id="xxx"))
        assert200(response)
        assert len(response.json["data"]) == 0

    def test_organization_role_api_get(self):
        """It should fetch an organization's roles list from the API"""
        response = self.get(url_for("api.org_roles"))
        assert200(response)

    def test_organization_api_get(self):
        """It should fetch an organization from the API"""
        organization = OrganizationFactory()
        response = self.get(url_for("api.organization", org=organization))
        assert200(response)

    def test_organization_api_get_deleted(self):
        """It should not fetch a deleted organization from the API"""
        organization = OrganizationFactory(deleted=datetime.utcnow())
        response = self.get(url_for("api.organization", org=organization))
        assert410(response)

    def test_organization_api_get_deleted_but_authorized(self):
        """It should fetch a deleted organization from the API if authorized"""
        user = self.login()
        member = Member(user=user, role="editor")
        organization = OrganizationFactory(deleted=datetime.utcnow(), members=[member])
        response = self.get(url_for("api.organization", org=organization))
        assert200(response)

    def test_organization_api_create(self):
        """It should create an organization from the API"""
        data = OrganizationFactory.as_dict()
        user = self.login()
        response = self.post(url_for("api.organizations"), data)
        assert201(response)
        assert Organization.objects.count() == 1

        org = Organization.objects.first()
        member = org.member(user)
        assert member is not None, "Current user should be a member"
        assert member.role == "admin", "Current user should be an administrator"
        assert org.get_metrics()["members"] == 1

    def test_organization_api_update(self):
        """It should update an organization from the API"""
        user = self.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        data = org.to_dict()
        data["description"] = "new description"
        response = self.put(url_for("api.organization", org=org), data)
        assert200(response)
        assert Organization.objects.count() == 1
        assert Organization.objects.first().description == "new description"

    def test_organization_api_update_business_number_id(self):
        """It should update an organization from the API by adding a business number id"""
        user = self.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        data = org.to_dict()
        data["business_number_id"] = "13002526500013"
        response = self.put(url_for("api.organization", org=org), data)
        assert200(response)
        assert Organization.objects.count() == 1
        assert Organization.objects.first().business_number_id == "13002526500013"

    def test_organization_api_update_business_number_id_failing(self):
        """It should update an organization from the API by adding a business number id"""
        user = self.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        data = org.to_dict()
        data["business_number_id"] = "110014016"
        response = self.put(url_for("api.organization", org=org), data)
        assert400(response)
        assert response.json["errors"]["business_number_id"][0] == _(
            "A siret number is made of 14 digits"
        )

        data["business_number_id"] = "12345678901234"
        response = self.put(url_for("api.organization", org=org), data)
        assert400(response)
        assert response.json["errors"]["business_number_id"][0] == _("Invalid Siret number")

        data["business_number_id"] = "tttttttttttttt"
        response = self.put(url_for("api.organization", org=org), data)
        assert400(response)
        assert response.json["errors"]["business_number_id"][0] == _(
            "A siret number is only made of digits"
        )

    def test_organization_api_update_deleted(self):
        """It should not update a deleted organization from the API"""
        org = OrganizationFactory(deleted=datetime.utcnow())
        data = org.to_dict()
        data["description"] = "new description"
        self.login()
        response = self.put(url_for("api.organization", org=org), data)
        assert410(response)
        assert Organization.objects.first().description == org.description

    def test_organization_api_update_forbidden(self):
        """It should not update an organization from the API if not admin"""
        org = OrganizationFactory()
        data = org.to_dict()
        data["description"] = "new description"
        self.login()
        response = self.put(url_for("api.organization", org=org), data)
        assert403(response)
        assert Organization.objects.count() == 1
        assert Organization.objects.first().description == org.description

    def test_organization_api_delete(self):
        """It should delete an organization from the API"""
        user = self.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        response = self.delete(url_for("api.organization", org=org))
        assert204(response)
        assert Organization.objects.count() == 1
        assert Organization.objects[0].deleted is not None

    def test_organization_api_delete_deleted(self):
        """It should not delete a deleted organization from the API"""
        self.login()
        organization = OrganizationFactory(deleted=datetime.utcnow())
        response = self.delete(url_for("api.organization", org=organization))
        assert410(response)
        assert Organization.objects[0].deleted is not None

    def test_organization_api_delete_as_editor_forbidden(self):
        """It should not delete an organization from the API if not admin"""
        user = self.login()
        member = Member(user=user, role="editor")
        org = OrganizationFactory(members=[member])
        response = self.delete(url_for("api.organization", org=org))
        assert403(response)
        assert Organization.objects.count() == 1
        assert Organization.objects[0].deleted is None

    def test_organization_api_delete_as_non_member_forbidden(self):
        """It should delete an organization from the API if not member"""
        self.login()
        org = OrganizationFactory()
        response = self.delete(url_for("api.organization", org=org))
        assert403(response)
        assert Organization.objects.count() == 1
        assert Organization.objects[0].deleted is None


class MembershipAPITest(PytestOnlyAPITestCase):
    def test_request_membership(self):
        organization = OrganizationFactory()
        user = self.login()
        data = {"comment": "a comment"}

        response = self.post(url_for("api.request_membership", org=organization), data)
        assert201(response)

        organization.reload()
        assert len(organization.requests) == 1
        assert len(organization.pending_requests) == 1
        assert len(organization.refused_requests) == 0
        assert len(organization.accepted_requests) == 0

        request = organization.requests[0]
        assert request.user == user
        assert request.status == "pending"
        assert request.comment == "a comment"
        assert request.handled_on is None
        assert request.handled_by is None
        assert request.refusal_comment is None

    def test_request_existing_pending_membership_do_not_duplicate_it(self):
        user = self.login()
        previous_request = MembershipRequest(user=user, comment="previous")
        organization = OrganizationFactory(requests=[previous_request])
        data = {"comment": "a comment"}

        response = self.post(url_for("api.request_membership", org=organization), data)
        assert200(response)

        organization.reload()
        assert len(organization.requests) == 1
        assert len(organization.pending_requests) == 1
        assert len(organization.refused_requests) == 0
        assert len(organization.accepted_requests) == 0

        request = organization.requests[0]
        assert request.user == user
        assert request.status == "pending"
        assert request.comment == "a comment"
        assert request.handled_on is None
        assert request.handled_by is None
        assert request.refusal_comment is None

    def test_get_membership_requests(self):
        user = self.login()
        applicant = UserFactory(email="thibaud@example.org")
        membership_request = MembershipRequest(user=applicant, comment="test")
        member = Member(user=user, role="admin")
        organization = OrganizationFactory(members=[member], requests=[membership_request])

        response = self.get(url_for("api.request_membership", org=organization))
        assert200(response)

        assert len(response.json) == 1
        assert response.json[0]["comment"] == "test"
        assert (
            response.json[0]["user"]["email"] == "th*****@example.org"
        )  # Can see partially obfuscated email of applicant

    def test_only_org_member_can_get_membership_requests(self):
        self.login()
        applicant = UserFactory(email="thibaud@example.org")
        membership_request = MembershipRequest(user=applicant, comment="test")
        organization = OrganizationFactory(members=[], requests=[membership_request])

        response = self.get(url_for("api.request_membership", org=organization))
        assert403(response)

    def test_applicant_can_get_their_membership_requests(self):
        applicant = self.login()
        membership_request = MembershipRequest(user=applicant, comment="test")
        organization = OrganizationFactory(members=[], requests=[membership_request])

        response = self.get(
            url_for("api.request_membership", org=organization),
            query_string={"user": str(applicant.id)},
        )
        assert200(response)

    @pytest.mark.parametrize(
        "searched_status",
        [
            "pending",
            "accepted",
            "refused",
        ],
    )
    def test_applicant_can_get_their_membership_requests_with_status(self, searched_status: str):
        applicant = self.login()
        membership_request = MembershipRequest(user=applicant, comment="test")
        organization = OrganizationFactory(members=[], requests=[membership_request])
        response = self.get(
            url_for("api.request_membership", org=organization),
            query_string={"user": str(applicant.id), "status": searched_status},
        )
        assert200(response)
        requests = response.json
        if searched_status == "pending":
            assert len(requests) == 1
        else:
            assert len(requests) == 0

    def test_get_members_with_or_without_email(self):
        admin = Member(
            user=UserFactory(email="admin@example.org"), role="admin", since="2024-04-14"
        )
        editor = Member(user=UserFactory(email="editor@example.org"), role="editor")
        other = UserFactory(email="other@example.org")

        organization = OrganizationFactory(members=[admin, editor])

        # Organization admin can partially see emails
        self.login(admin.user)
        response = self.get(url_for("api.organization", org=organization))
        assert200(response)

        members = response.json["members"]
        assert len(members) == 2
        assert members[0]["role"] == "admin"
        assert members[0]["since"] == "2024-04-14T00:00:00+00:00"
        assert members[0]["user"]["email"] == "ad***@example.org"

        assert members[1]["role"] == "editor"
        assert members[1]["user"]["email"] == "ed****@example.org"

        # Organization editor can partially see emails
        self.login(editor.user)
        response = self.get(url_for("api.organization", org=organization))
        assert200(response)

        members = response.json["members"]
        assert len(members) == 2
        assert members[0]["role"] == "admin"
        assert members[0]["since"] == "2024-04-14T00:00:00+00:00"
        assert members[0]["user"]["email"] == "ad***@example.org"

        assert members[1]["role"] == "editor"
        assert members[1]["user"]["email"] == "ed****@example.org"

        # Others cannot see emails
        self.login(other)
        response = self.get(url_for("api.organization", org=organization))
        assert200(response)

        members = response.json["members"]
        assert len(members) == 2
        assert members[0]["role"] == "admin"
        assert members[0]["since"] == "2024-04-14T00:00:00+00:00"
        assert members[0]["user"]["email"] == "***@example.org"

        assert members[1]["role"] == "editor"
        assert members[1]["user"]["email"] == "***@example.org"

        # Super admin of udata can see emails
        self.login(AdminFactory())
        response = self.get(url_for("api.organization", org=organization))
        assert200(response)

        members = response.json["members"]
        assert len(members) == 2
        assert members[0]["role"] == "admin"
        assert members[0]["since"] == "2024-04-14T00:00:00+00:00"
        assert members[0]["user"]["email"] == "admin@example.org"

        assert members[1]["role"] == "editor"
        assert members[1]["user"]["email"] == "editor@example.org"

    def test_accept_membership(self):
        user = self.login()
        applicant = UserFactory()
        membership_request = MembershipRequest(user=applicant, comment="test")
        member = Member(user=user, role="admin")
        organization = OrganizationFactory(members=[member], requests=[membership_request])

        api_url = url_for("api.accept_membership", org=organization, id=membership_request.id)
        response = self.post(api_url)
        assert200(response)

        assert response.json["role"] == "editor"

        organization.reload()
        assert len(organization.requests) == 1
        assert len(organization.pending_requests) == 0
        assert len(organization.refused_requests) == 0
        assert len(organization.accepted_requests) == 1
        assert organization.is_member(applicant)

        request = organization.requests[0]
        assert request.user == applicant
        assert request.status == "accepted"
        assert request.comment == "test"
        assert request.handled_by == user
        assert request.handled_on is not None
        assert request.refusal_comment is None

        # test accepting twice will raise 409
        api_url = url_for("api.accept_membership", org=organization, id=membership_request.id)
        response = self.post(api_url)
        assert_status(response, 409)

    def test_only_admin_can_accept_membership(self):
        user = self.login()
        applicant = UserFactory()
        membership_request = MembershipRequest(user=applicant, comment="test")
        member = Member(user=user, role="editor")
        organization = OrganizationFactory(members=[member], requests=[membership_request])

        api_url = url_for("api.accept_membership", org=organization, id=membership_request.id)
        response = self.post(api_url)
        assert403(response)

    def test_accept_membership_404(self):
        user = self.login()
        member = Member(user=user, role="admin")
        organization = OrganizationFactory(members=[member])

        api_url = url_for("api.accept_membership", org=organization, id=MembershipRequest().id)
        response = self.post(api_url)
        assert404(response)

        assert response.json["message"] == "Unknown membership request id"

    def test_refuse_membership(self):
        user = self.login()
        applicant = UserFactory()
        membership_request = MembershipRequest(user=applicant, comment="test")
        member = Member(user=user, role="admin")
        organization = OrganizationFactory(members=[member], requests=[membership_request])
        data = {"comment": "no"}

        api_url = url_for("api.refuse_membership", org=organization, id=membership_request.id)
        response = self.post(api_url, data)
        assert200(response)

        organization.reload()
        assert len(organization.requests) == 1
        assert len(organization.pending_requests) == 0
        assert len(organization.refused_requests) == 1
        assert len(organization.accepted_requests) == 0
        assert not organization.is_member(applicant)

        request = organization.requests[0]
        assert request.user == applicant
        assert request.status == "refused"
        assert request.comment == "test"
        assert request.refusal_comment == "no"
        assert request.handled_by == user
        assert request.handled_on is not None

    def test_only_admin_can_refuse_membership(self):
        user = self.login()
        applicant = UserFactory()
        membership_request = MembershipRequest(user=applicant, comment="test")
        member = Member(user=user, role="editor")
        organization = OrganizationFactory(members=[member], requests=[membership_request])
        data = {"comment": "no"}

        api_url = url_for("api.refuse_membership", org=organization, id=membership_request.id)
        response = self.post(api_url, data)
        assert403(response)

    def test_refuse_membership_404(self):
        user = self.login()
        member = Member(user=user, role="admin")
        organization = OrganizationFactory(members=[member])

        api_url = url_for("api.refuse_membership", org=organization, id=MembershipRequest().id)
        response = self.post(api_url)
        assert404(response)

        assert response.json["message"] == "Unknown membership request id"

    def test_create_member(self):
        user = self.login()
        added_user = UserFactory()
        organization = OrganizationFactory(
            members=[
                Member(user=user, role="admin"),
            ]
        )

        api_url = url_for("api.member", org=organization, user=added_user)
        response = self.post(api_url, {"role": "admin"})

        assert201(response)

        assert response.json["role"] == "admin"

        organization.reload()
        assert organization.is_member(added_user)
        assert organization.is_admin(added_user)
        assert organization.get_metrics()["members"] == 2

    def test_only_admin_can_create_member(self):
        user = self.login()
        added_user = UserFactory()
        organization = OrganizationFactory(
            members=[
                Member(user=user, role="editor"),
            ]
        )

        api_url = url_for("api.member", org=organization, user=added_user)
        response = self.post(api_url, {"role": "editor"})

        assert403(response)

        organization.reload()
        assert not organization.is_member(added_user)

    def test_create_member_exists(self):
        user = self.login()
        added_user = UserFactory()
        organization = OrganizationFactory(
            members=[Member(user=user, role="admin"), Member(user=added_user, role="editor")]
        )

        api_url = url_for("api.member", org=organization, user=added_user)
        response = self.post(api_url, {"role": "admin"})

        assert_status(response, 409)

        assert response.json["role"] == "editor"

        organization.reload()
        assert organization.is_member(added_user)
        assert not organization.is_admin(added_user)

    def test_update_member(self):
        user = self.login()
        updated_user = UserFactory()
        organization = OrganizationFactory(
            members=[Member(user=user, role="admin"), Member(user=updated_user, role="editor")]
        )

        api_url = url_for("api.member", org=organization, user=updated_user)
        response = self.put(api_url, {"role": "admin"})

        assert200(response)

        assert response.json["role"] == "admin"

        organization.reload()
        assert organization.is_member(updated_user)
        assert organization.is_admin(updated_user)

    def test_only_admin_can_update_member(self):
        user = self.login()
        updated_user = UserFactory()
        organization = OrganizationFactory(
            members=[Member(user=user, role="editor"), Member(user=updated_user, role="editor")]
        )

        api_url = url_for("api.member", org=organization, user=updated_user)
        response = self.put(api_url, {"role": "admin"})

        assert403(response)

        organization.reload()
        assert organization.is_member(updated_user)
        assert not organization.is_admin(updated_user)

    def test_delete_member(self):
        user = self.login()
        deleted_user = UserFactory()
        organization = OrganizationFactory(
            members=[Member(user=user, role="admin"), Member(user=deleted_user, role="editor")]
        )

        api_url = url_for("api.member", org=organization, user=deleted_user)
        response = self.delete(api_url)
        assert204(response)

        organization.reload()
        assert not organization.is_member(deleted_user)
        assert organization.get_metrics()["members"] == 1

    def test_only_admin_can_delete_member(self):
        user = self.login()
        deleted_user = UserFactory()
        organization = OrganizationFactory(
            members=[Member(user=user, role="editor"), Member(user=deleted_user, role="editor")]
        )

        api_url = url_for("api.member", org=organization, user=deleted_user)
        response = self.delete(api_url)
        assert403(response)

        organization.reload()
        assert organization.is_member(deleted_user)

    def test_follow_org(self):
        """It should follow an organization on POST"""
        user = self.login()
        to_follow = OrganizationFactory()

        url = url_for("api.organization_followers", id=to_follow.id)
        response = self.post(url)
        assert201(response)

        to_follow.count_followers()
        assert to_follow.get_metrics()["followers"] == 1

        assert Follow.objects.following(to_follow).count() == 0
        assert Follow.objects.followers(to_follow).count() == 1
        follow = Follow.objects.followers(to_follow).first()
        assert isinstance(follow.following, Organization)
        assert Follow.objects.following(user).count() == 1
        assert Follow.objects.followers(user).count() == 0

    def test_unfollow_org(self):
        """It should unfollow the organization on DELETE"""
        user = self.login()
        to_follow = OrganizationFactory()
        Follow.objects.create(follower=user, following=to_follow)

        url = url_for("api.organization_followers", id=to_follow.id)
        response = self.delete(url)
        assert200(response)

        nb_followers = Follow.objects.followers(to_follow).count()

        assert nb_followers == 0
        assert response.json["followers"] == nb_followers

        assert Follow.objects.following(to_follow).count() == 0
        assert Follow.objects.following(user).count() == 0
        assert Follow.objects.followers(user).count() == 0

    def test_suggest_organizations_api(self):
        """It should suggest organizations"""
        for i in range(3):
            OrganizationFactory(
                name="test-{0}".format(i) if i % 2 else faker.word(), metrics={"followers": i}
            )
        max_follower_organization = OrganizationFactory(name="test-4", metrics={"followers": 10})
        response = self.get(url_for("api.suggest_organizations", q="tes", size=5))
        assert200(response)

        assert len(response.json) <= 5
        assert len(response.json) > 1

        for suggestion in response.json:
            assert "id" in suggestion
            assert "slug" in suggestion
            assert "name" in suggestion
            assert "image_url" in suggestion
            assert "acronym" in suggestion
            assert "tes" in suggestion["name"]
            assert response.json[0]["id"] == str(max_follower_organization.id)

    def test_suggest_organizations_with_special_chars(self):
        """It should suggest organizations with special caracters"""
        for i in range(4):
            OrganizationFactory(name="testé-{0}".format(i) if i % 2 else faker.word())

        response = self.get(url_for("api.suggest_organizations", q="testé", size=5))
        assert200(response)

        assert len(response.json) <= 5
        assert len(response.json) > 1

        for suggestion in response.json:
            assert "id" in suggestion
            assert "slug" in suggestion
            assert "name" in suggestion
            assert "image_url" in suggestion
            assert "testé" in suggestion["name"]

    def test_suggest_organizations_with_multiple_words(self):
        """It should suggest organizations with words"""
        for i in range(4):
            OrganizationFactory(name="mon testé-{0}".format(i) if i % 2 else faker.word())

        response = self.get(url_for("api.suggest_organizations", q="mon testé", size=5))
        assert200(response)

        assert len(response.json) <= 5
        assert len(response.json) > 1

        for suggestion in response.json:
            assert "id" in suggestion
            assert "slug" in suggestion
            assert "name" in suggestion
            assert "image_url" in suggestion
            assert "mon testé" in suggestion["name"]

    def test_suggest_organizations_with_apostrophe(self):
        """It should suggest organizations with words"""
        for i in range(4):
            OrganizationFactory(
                name="Ministère de l'intérieur {0}".format(i) if i % 2 else faker.word()
            )

        response = self.get(url_for("api.suggest_organizations", q="Ministère", size=5))
        assert200(response)

        assert len(response.json) <= 5
        assert len(response.json) > 1

        for suggestion in response.json:
            assert "id" in suggestion
            assert "slug" in suggestion
            assert "name" in suggestion
            assert "image_url" in suggestion
            assert "Ministère" in suggestion["name"]

    def test_suggest_organizations_api_no_match(self):
        """It should not provide organization suggestion if no match"""
        OrganizationFactory.create_batch(3)

        response = self.get(url_for("api.suggest_organizations", q="xxxxxx", size=5))
        assert200(response)
        assert len(response.json) == 0

    def test_suggest_organizations_api_empty(self):
        """It should not provide organization suggestion if no data"""
        response = self.get(url_for("api.suggest_organizations", q="xxxxxx", size=5))
        assert200(response)
        assert len(response.json) == 0

    def test_suggest_organizations_homonyms(self):
        """It should suggest organizations and not deduplicate homonyms"""
        OrganizationFactory.create_batch(2, name="homonym")

        response = self.get(url_for("api.suggest_organizations", q="homonym", size=5))
        assert200(response)

        assert len(response.json) == 2

        for suggestion in response.json:
            assert suggestion["name"] == "homonym"

    def test_suggest_organizations_acronym(self):
        """Should suggest organizations based on acronym"""

        for i in range(3):
            OrganizationFactory(
                name=faker.word(),
                acronym=f"UDATA{i}" if i % 2 else faker.word(),
                metrics={"followers": i},
            )
        max_follower_organization = OrganizationFactory(
            name=faker.word(), acronym="UDATA4", metrics={"followers": 10}
        )
        response = self.get(url_for("api.suggest_organizations", q="uDaTa", size=5))
        assert200(response)

        assert len(response.json) == 2

        for suggestion in response.json:
            assert "id" in suggestion
            assert "slug" in suggestion
            assert "name" in suggestion
            assert "image_url" in suggestion
            assert "acronym" in suggestion
            assert "UDATA" in suggestion["acronym"]
            assert response.json[0]["id"] == str(max_follower_organization.id)


class OrganizationDatasetsAPITest(PytestOnlyAPITestCase):
    def test_list_org_datasets(self):
        """Should list organization datasets"""
        org = OrganizationFactory()
        datasets = DatasetFactory.create_batch(3, organization=org)

        response = self.get(url_for("api.org_datasets", org=org))

        assert200(response)
        assert len(response.json["data"]) == len(datasets)

    def test_list_org_datasets_private(self):
        """Should include private datasets when member"""
        user = self.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        datasets = DatasetFactory.create_batch(3, organization=org, private=True)

        response = self.get(url_for("api.org_datasets", org=org))

        assert200(response)
        assert len(response.json["data"]) == len(datasets)

    def test_list_org_datasets_hide_private(self):
        """Should not include private datasets when not member"""
        org = OrganizationFactory()
        datasets = DatasetFactory.create_batch(3, organization=org)
        DatasetFactory.create_batch(2, organization=org, private=True)

        response = self.get(url_for("api.org_datasets", org=org))

        assert200(response)
        assert len(response.json["data"]) == len(datasets)

    def test_list_org_datasets_with_size(self):
        """Should list organization datasets"""
        org = OrganizationFactory()
        DatasetFactory.create_batch(3, organization=org)

        response = self.get(url_for("api.org_datasets", org=org, page_size=2))

        assert200(response)
        assert len(response.json["data"]) == 2


class OrganizationReusesAPITest(PytestOnlyAPITestCase):
    def test_list_org_reuses(self):
        """Should list organization reuses"""
        org = OrganizationFactory()
        reuses = ReuseFactory.create_batch(3, organization=org)

        response = self.get(url_for("api.org_reuses", org=org))

        assert200(response)
        assert len(response.json) == len(reuses)

    def test_list_org_reuses_private(self):
        """Should include private reuses when member"""
        user = self.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        reuses = ReuseFactory.create_batch(3, organization=org, private=True)

        response = self.get(url_for("api.org_reuses", org=org))

        assert200(response)
        assert len(response.json) == len(reuses)

    def test_list_org_reuses_hide_private(self):
        """Should not include private reuses when not member"""
        org = OrganizationFactory()
        reuses = ReuseFactory.create_batch(3, organization=org)
        ReuseFactory.create_batch(2, organization=org, private=True)

        response = self.get(url_for("api.org_reuses", org=org))

        assert200(response)
        assert len(response.json) == len(reuses)


class OrganizationDiscussionsAPITest(PytestOnlyAPITestCase):
    def test_list_org_discussions(self):
        """Should list organization discussions"""
        user = UserFactory()
        org = OrganizationFactory()
        reuse = ReuseFactory(organization=org)
        dataset = DatasetFactory(organization=org)
        discussions = [
            Discussion.objects.create(subject=dataset, title="", user=user),
            Discussion.objects.create(subject=reuse, title="", user=user),
        ]

        response = self.get(url_for("api.org_discussions", org=org))

        assert200(response)
        assert len(response.json) == len(discussions)

        discussions_ids = [str(d.id) for d in discussions]
        for discussion in response.json:
            assert discussion["id"] in discussions_ids


class OrganizationBadgeAPITest(PytestOnlyAPITestCase):
    @pytest.fixture(autouse=True)
    def setup_func(self):
        self.factory = badge_factory(Organization)
        self.user = self.login(AdminFactory())
        self.organization = OrganizationFactory()

    def test_list(self):
        response = self.get(url_for("api.available_organization_badges"))
        assert200(response)
        assert len(response.json) == len(Organization.__badges__)
        for kind, label in Organization.__badges__.items():
            assert kind in response.json
            assert response.json[kind] == label

    def test_create(self):
        data = self.factory.as_dict()
        url = url_for("api.organization_badges", org=self.organization)
        with assert_emit(on_badge_added):
            response = self.post(url, data)
            assert201(response)
        self.organization.reload()
        assert len(self.organization.badges) == 1

    def test_create_same(self):
        data = self.factory.as_dict()
        url = url_for("api.organization_badges", org=self.organization)
        with assert_emit(on_badge_added):
            self.post(url, data)
        with assert_not_emit(on_badge_added):
            response = self.post(url, data)
            assert200(response)
        self.organization.reload()
        assert len(self.organization.badges) == 1

    def test_create_2nd(self):
        # Explicitely setting the kind to avoid collisions given the
        # small number of choices for kinds.
        kinds_keys = list(Organization.__badges__)
        self.organization.add_badge(kinds_keys[0])
        data = self.factory.as_dict()
        data["kind"] = kinds_keys[1]
        url = url_for("api.organization_badges", org=self.organization)
        response = self.post(url, data)
        assert201(response)
        self.organization.reload()
        assert len(self.organization.badges) == 2

    def test_delete(self):
        badge = self.factory()
        self.organization.add_badge(badge.kind)
        self.organization.save()
        url = url_for("api.organization_badge", org=self.organization, badge_kind=str(badge.kind))
        with assert_emit(on_badge_removed):
            response = self.delete(url)
            assert204(response)
        self.organization.reload()
        assert len(self.organization.badges) == 0

    def test_delete_404(self):
        kind = str(self.factory().kind)
        url = url_for("api.organization_badge", org=self.organization, badge_kind=kind)
        response = self.delete(url)
        assert404(response)


class OrganizationContactPointsAPITest(PytestOnlyAPITestCase):
    def test_org_contact_points(self):
        user = self.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        data = {
            "email": "mooneywayne@cobb-cochran.com",
            "name": "Martin Schultz",
            "organization": str(org.id),
            "role": "contact",
        }
        response = self.post(url_for("api.contact_points"), data)
        assert201(response)

        response = self.get(url_for("api.org_contact_points", org=org))
        assert200(response)

        assert response.json["data"][0]["name"] == data["name"]
        assert response.json["data"][0]["email"] == data["email"]

    def test_org_contact_points_suggest(self):
        user = self.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        data = {
            "email": "mooneywayne@cobb-cochran.com",
            "name": "Martin Schultz",
            "organization": str(org.id),
            "role": "contact",
        }
        response = self.post(url_for("api.contact_points"), data)
        assert201(response)

        response = self.get(url_for("api.suggest_org_contact_points", org=org, q="mooneywayne"))
        assert200(response)

        assert response.json[0]["name"] == data["name"]
        assert response.json[0]["email"] == data["email"]

        response = self.get(
            url_for("api.suggest_org_contact_points", org=org, q="mooneeejnknywayne")
        )
        assert200(response)

        assert len(response.json) == 0


class OrganizationCsvExportsTest(PytestOnlyAPITestCase):
    def test_datasets_csv(self):
        org = OrganizationFactory()
        [DatasetFactory(organization=org, resources=[ResourceFactory()]) for _ in range(3)]

        response = self.get(url_for("api.organization_datasets_csv", org=org))

        assert200(response)
        assert response.mimetype == "text/csv"
        assert response.charset == "utf-8"

        csvfile = StringIO(response.data.decode("utf-8"))
        reader = csv.get_reader(csvfile)
        header = next(reader)

        assert header[0] == "id"
        assert "title" in header
        assert "url" in header
        assert "description" in header
        assert "created_at" in header
        assert "last_modified" in header
        assert "tags" in header
        assert "metric.reuses" in header

    def test_resources_csv(self):
        org = OrganizationFactory()
        datasets = [
            DatasetFactory(organization=org, resources=[ResourceFactory(), ResourceFactory()])
            for _ in range(3)
        ]
        not_org_dataset = DatasetFactory(resources=[ResourceFactory()])
        hidden_dataset = DatasetFactory(private=True)

        response = self.get(url_for("api.organization_datasets_resources_csv", org=org))

        assert200(response)
        assert response.mimetype == "text/csv"
        assert response.charset == "utf-8"

        csvfile = StringIO(response.data.decode("utf-8"))
        reader = csv.get_reader(csvfile)
        header = next(reader)

        assert header[0] == "dataset.id"
        assert "dataset.title" in header
        assert "dataset.url" in header
        assert "title" in header
        assert "filetype" in header
        assert "url" in header
        assert "created_at" in header
        assert "modified" in header
        assert "downloads" in header

        resource_id_index = header.index("id")

        rows = list(reader)
        ids = [(row[0], row[resource_id_index]) for row in rows]

        assert len(rows) == sum(len(d.resources) for d in datasets)
        for dataset in datasets:
            for resource in dataset.resources:
                assert (str(dataset.id), str(resource.id)) in ids

        dataset_ids = set(row[0] for row in rows)
        assert str(hidden_dataset.id) not in dataset_ids
        assert str(not_org_dataset.id) not in dataset_ids

    def test_dataservices_csv(self):
        org = OrganizationFactory()
        [DataserviceFactory(organization=org) for _ in range(3)]

        response = self.get(url_for("api.organization_dataservices_csv", org=org))

        assert200(response)
        assert response.mimetype == "text/csv"
        assert response.charset == "utf-8"

        csvfile = StringIO(response.data.decode("utf-8"))
        reader = csv.get_reader(csvfile)
        header = next(reader)

        assert header[0] == "id"
        assert "title" in header
        assert "url" in header
        assert "description" in header
        assert "created_at" in header
        assert "metadata_modified_at" in header
        assert "tags" in header
        assert "metric.views" in header
        assert "datasets" in header

    def test_discussions_csv_content_empty(self):
        organization = OrganizationFactory()
        response = self.get(url_for("api.organization_discussions_csv", org=organization))
        assert200(response)

        assert response.data.decode("utf8") == (
            '"id";"user";"subject";"subject_class";"subject_id";"title";"size";"participants";'
            '"messages";"created";"closed";"closed_by";"closed_by_id";"closed_by_organization";'
            '"closed_by_organization_id"\r\n'
        )

    def test_discussions_csv_content_filled(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        user = UserFactory(first_name="John", last_name="Snow")
        discussion = DiscussionFactory(subject=dataset, user=user)
        response = self.get(url_for("api.organization_discussions_csv", org=organization))
        assert200(response)

        headers, data = response.data.decode("utf-8").strip().split("\r\n")
        expected = '"{discussion.id}";"{discussion.user}"'
        assert_starts_with(data, expected.format(discussion=discussion))
