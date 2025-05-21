from datetime import datetime
from io import StringIO

import pytest
from flask import url_for

import udata.core.organization.constants as org_constants
from udata.core import csv
from udata.core.badges.factories import badge_factory
from udata.core.badges.signals import on_badge_added, on_badge_removed
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.discussions.factories import DiscussionFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.i18n import _
from udata.models import Discussion, Follow, Member, MembershipRequest, Organization
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

pytestmark = [
    pytest.mark.usefixtures("clean_db"),
]


class OrganizationAPITest:
    modules = []

    def test_organization_api_list(self, api):
        """It should fetch an organization list from the API"""
        organizations = OrganizationFactory.create_batch(3)

        response = api.get(url_for("api.organizations"))
        assert200(response)
        len(response.json["data"]) == len(organizations)

    def test_organization_api_list_with_filters(self, api):
        """It should filter the organization list"""
        _org = OrganizationFactory()
        org_public_service = OrganizationFactory()
        org_public_service.add_badge(org_constants.PUBLIC_SERVICE)

        response = api.get(url_for("api.organizations", badge=org_constants.PUBLIC_SERVICE))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(org_public_service.id)

        response = api.get(url_for("api.organizations", badge="bad-badge"))
        assert400(response)

    def test_organization_role_api_get(self, api):
        """It should fetch an organization's roles list from the API"""
        response = api.get(url_for("api.org_roles"))
        assert200(response)

    def test_organization_api_get(self, api):
        """It should fetch an organization from the API"""
        organization = OrganizationFactory()
        response = api.get(url_for("api.organization", org=organization))
        assert200(response)

    def test_organization_api_get_deleted(self, api):
        """It should not fetch a deleted organization from the API"""
        organization = OrganizationFactory(deleted=datetime.utcnow())
        response = api.get(url_for("api.organization", org=organization))
        assert410(response)

    def test_organization_api_get_deleted_but_authorized(self, api):
        """It should fetch a deleted organization from the API if authorized"""
        user = api.login()
        member = Member(user=user, role="editor")
        organization = OrganizationFactory(deleted=datetime.utcnow(), members=[member])
        response = api.get(url_for("api.organization", org=organization))
        assert200(response)

    def test_organization_api_create(self, api):
        """It should create an organization from the API"""
        data = OrganizationFactory.as_dict()
        user = api.login()
        response = api.post(url_for("api.organizations"), data)
        assert201(response)
        assert Organization.objects.count() == 1

        org = Organization.objects.first()
        member = org.member(user)
        assert member is not None, "Current user should be a member"
        assert member.role == "admin", "Current user should be an administrator"
        assert org.get_metrics()["members"] == 1

    def test_organization_api_update(self, api):
        """It should update an organization from the API"""
        user = api.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        data = org.to_dict()
        data["description"] = "new description"
        response = api.put(url_for("api.organization", org=org), data)
        assert200(response)
        assert Organization.objects.count() == 1
        assert Organization.objects.first().description == "new description"

    def test_organization_api_update_business_number_id(self, api):
        """It should update an organization from the API by adding a business number id"""
        user = api.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        data = org.to_dict()
        data["business_number_id"] = "13002526500013"
        response = api.put(url_for("api.organization", org=org), data)
        assert200(response)
        assert Organization.objects.count() == 1
        assert Organization.objects.first().business_number_id == "13002526500013"

    def test_organization_api_update_business_number_id_failing(self, api):
        """It should update an organization from the API by adding a business number id"""
        user = api.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        data = org.to_dict()
        data["business_number_id"] = "110014016"
        response = api.put(url_for("api.organization", org=org), data)
        assert400(response)
        assert response.json["errors"]["business_number_id"][0] == _(
            "A siret number is made of 14 digits"
        )

        data["business_number_id"] = "12345678901234"
        response = api.put(url_for("api.organization", org=org), data)
        assert400(response)
        assert response.json["errors"]["business_number_id"][0] == _("Invalid Siret number")

        data["business_number_id"] = "tttttttttttttt"
        response = api.put(url_for("api.organization", org=org), data)
        assert400(response)
        assert response.json["errors"]["business_number_id"][0] == _(
            "A siret number is only made of digits"
        )

    def test_organization_api_update_deleted(self, api):
        """It should not update a deleted organization from the API"""
        org = OrganizationFactory(deleted=datetime.utcnow())
        data = org.to_dict()
        data["description"] = "new description"
        api.login()
        response = api.put(url_for("api.organization", org=org), data)
        assert410(response)
        assert Organization.objects.first().description == org.description

    def test_organization_api_update_forbidden(self, api):
        """It should not update an organization from the API if not admin"""
        org = OrganizationFactory()
        data = org.to_dict()
        data["description"] = "new description"
        api.login()
        response = api.put(url_for("api.organization", org=org), data)
        assert403(response)
        assert Organization.objects.count() == 1
        assert Organization.objects.first().description == org.description

    def test_organization_api_delete(self, api):
        """It should delete an organization from the API"""
        user = api.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        response = api.delete(url_for("api.organization", org=org))
        assert204(response)
        assert Organization.objects.count() == 1
        assert Organization.objects[0].deleted is not None

    def test_organization_api_delete_deleted(self, api):
        """It should not delete a deleted organization from the API"""
        api.login()
        organization = OrganizationFactory(deleted=datetime.utcnow())
        response = api.delete(url_for("api.organization", org=organization))
        assert410(response)
        assert Organization.objects[0].deleted is not None

    def test_organization_api_delete_as_editor_forbidden(self, api):
        """It should not delete an organization from the API if not admin"""
        user = api.login()
        member = Member(user=user, role="editor")
        org = OrganizationFactory(members=[member])
        response = api.delete(url_for("api.organization", org=org))
        assert403(response)
        assert Organization.objects.count() == 1
        assert Organization.objects[0].deleted is None

    def test_organization_api_delete_as_non_member_forbidden(self, api):
        """It should delete an organization from the API if not member"""
        api.login()
        org = OrganizationFactory()
        response = api.delete(url_for("api.organization", org=org))
        assert403(response)
        assert Organization.objects.count() == 1
        assert Organization.objects[0].deleted is None


class MembershipAPITest:
    modules = []

    def test_request_membership(self, api):
        organization = OrganizationFactory()
        user = api.login()
        data = {"comment": "a comment"}

        response = api.post(url_for("api.request_membership", org=organization), data)
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

    def test_request_existing_pending_membership_do_not_duplicate_it(self, api):
        user = api.login()
        previous_request = MembershipRequest(user=user, comment="previous")
        organization = OrganizationFactory(requests=[previous_request])
        data = {"comment": "a comment"}

        response = api.post(url_for("api.request_membership", org=organization), data)
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

    def test_get_membership_requests(self, api):
        user = api.login()
        applicant = UserFactory(email="thibaud@example.org")
        membership_request = MembershipRequest(user=applicant, comment="test")
        member = Member(user=user, role="admin")
        organization = OrganizationFactory(members=[member], requests=[membership_request])

        response = api.get(url_for("api.request_membership", org=organization))
        assert200(response)

        assert len(response.json) == 1
        assert response.json[0]["comment"] == "test"
        assert (
            response.json[0]["user"]["email"] == "th*****@example.org"
        )  # Can see partially obfuscated email of applicant

    def test_only_org_member_can_get_membership_requests(self, api):
        api.login()
        applicant = UserFactory(email="thibaud@example.org")
        membership_request = MembershipRequest(user=applicant, comment="test")
        organization = OrganizationFactory(members=[], requests=[membership_request])

        response = api.get(url_for("api.request_membership", org=organization))
        assert403(response)

    def test_applicant_can_get_their_membership_requests(self, api):
        applicant = api.login()
        membership_request = MembershipRequest(user=applicant, comment="test")
        organization = OrganizationFactory(members=[], requests=[membership_request])

        response = api.get(
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
    def test_applicant_can_get_their_membership_requests_with_status(
        self, api, searched_status: str
    ):
        applicant = api.login()
        membership_request = MembershipRequest(user=applicant, comment="test")
        organization = OrganizationFactory(members=[], requests=[membership_request])
        response = api.get(
            url_for("api.request_membership", org=organization),
            query_string={"user": str(applicant.id), "status": searched_status},
        )
        assert200(response)
        requests = response.json
        if searched_status == "pending":
            assert len(requests) == 1
        else:
            assert len(requests) == 0

    def test_get_members_with_or_without_email(self, api):
        admin = Member(
            user=UserFactory(email="admin@example.org"), role="admin", since="2024-04-14"
        )
        editor = Member(user=UserFactory(email="editor@example.org"), role="editor")
        other = UserFactory(email="other@example.org")

        organization = OrganizationFactory(members=[admin, editor])

        # Organization admin can partially see emails
        api.login(admin.user)
        response = api.get(url_for("api.organization", org=organization))
        assert200(response)

        members = response.json["members"]
        assert len(members) == 2
        assert members[0]["role"] == "admin"
        assert members[0]["since"] == "2024-04-14T00:00:00+00:00"
        assert members[0]["user"]["email"] == "ad***@example.org"

        assert members[1]["role"] == "editor"
        assert members[1]["user"]["email"] == "ed****@example.org"

        # Organization editor can partially see emails
        api.login(editor.user)
        response = api.get(url_for("api.organization", org=organization))
        assert200(response)

        members = response.json["members"]
        assert len(members) == 2
        assert members[0]["role"] == "admin"
        assert members[0]["since"] == "2024-04-14T00:00:00+00:00"
        assert members[0]["user"]["email"] == "ad***@example.org"

        assert members[1]["role"] == "editor"
        assert members[1]["user"]["email"] == "ed****@example.org"

        # Others cannot see emails
        api.login(other)
        response = api.get(url_for("api.organization", org=organization))
        assert200(response)

        members = response.json["members"]
        assert len(members) == 2
        assert members[0]["role"] == "admin"
        assert members[0]["since"] == "2024-04-14T00:00:00+00:00"
        assert members[0]["user"]["email"] == "***@example.org"

        assert members[1]["role"] == "editor"
        assert members[1]["user"]["email"] == "***@example.org"

        # Super admin of udata can see emails
        api.login(AdminFactory())
        response = api.get(url_for("api.organization", org=organization))
        assert200(response)

        members = response.json["members"]
        assert len(members) == 2
        assert members[0]["role"] == "admin"
        assert members[0]["since"] == "2024-04-14T00:00:00+00:00"
        assert members[0]["user"]["email"] == "admin@example.org"

        assert members[1]["role"] == "editor"
        assert members[1]["user"]["email"] == "editor@example.org"

    def test_accept_membership(self, api):
        user = api.login()
        applicant = UserFactory()
        membership_request = MembershipRequest(user=applicant, comment="test")
        member = Member(user=user, role="admin")
        organization = OrganizationFactory(members=[member], requests=[membership_request])

        api_url = url_for("api.accept_membership", org=organization, id=membership_request.id)
        response = api.post(api_url)
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
        response = api.post(api_url)
        assert_status(response, 409)

    def test_only_admin_can_accept_membership(self, api):
        user = api.login()
        applicant = UserFactory()
        membership_request = MembershipRequest(user=applicant, comment="test")
        member = Member(user=user, role="editor")
        organization = OrganizationFactory(members=[member], requests=[membership_request])

        api_url = url_for("api.accept_membership", org=organization, id=membership_request.id)
        response = api.post(api_url)
        assert403(response)

    def test_accept_membership_404(self, api):
        user = api.login()
        member = Member(user=user, role="admin")
        organization = OrganizationFactory(members=[member])

        api_url = url_for("api.accept_membership", org=organization, id=MembershipRequest().id)
        response = api.post(api_url)
        assert404(response)

        assert response.json["message"] == "Unknown membership request id"

    def test_refuse_membership(self, api):
        user = api.login()
        applicant = UserFactory()
        membership_request = MembershipRequest(user=applicant, comment="test")
        member = Member(user=user, role="admin")
        organization = OrganizationFactory(members=[member], requests=[membership_request])
        data = {"comment": "no"}

        api_url = url_for("api.refuse_membership", org=organization, id=membership_request.id)
        response = api.post(api_url, data)
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

    def test_only_admin_can_refuse_membership(self, api):
        user = api.login()
        applicant = UserFactory()
        membership_request = MembershipRequest(user=applicant, comment="test")
        member = Member(user=user, role="editor")
        organization = OrganizationFactory(members=[member], requests=[membership_request])
        data = {"comment": "no"}

        api_url = url_for("api.refuse_membership", org=organization, id=membership_request.id)
        response = api.post(api_url, data)
        assert403(response)

    def test_refuse_membership_404(self, api):
        user = api.login()
        member = Member(user=user, role="admin")
        organization = OrganizationFactory(members=[member])

        api_url = url_for("api.refuse_membership", org=organization, id=MembershipRequest().id)
        response = api.post(api_url)
        assert404(response)

        assert response.json["message"] == "Unknown membership request id"

    def test_create_member(self, api):
        user = api.login()
        added_user = UserFactory()
        organization = OrganizationFactory(
            members=[
                Member(user=user, role="admin"),
            ]
        )

        api_url = url_for("api.member", org=organization, user=added_user)
        response = api.post(api_url, {"role": "admin"})

        assert201(response)

        assert response.json["role"] == "admin"

        organization.reload()
        assert organization.is_member(added_user)
        assert organization.is_admin(added_user)
        assert organization.get_metrics()["members"] == 2

    def test_only_admin_can_create_member(self, api):
        user = api.login()
        added_user = UserFactory()
        organization = OrganizationFactory(
            members=[
                Member(user=user, role="editor"),
            ]
        )

        api_url = url_for("api.member", org=organization, user=added_user)
        response = api.post(api_url, {"role": "editor"})

        assert403(response)

        organization.reload()
        assert not organization.is_member(added_user)

    def test_create_member_exists(self, api):
        user = api.login()
        added_user = UserFactory()
        organization = OrganizationFactory(
            members=[Member(user=user, role="admin"), Member(user=added_user, role="editor")]
        )

        api_url = url_for("api.member", org=organization, user=added_user)
        response = api.post(api_url, {"role": "admin"})

        assert_status(response, 409)

        assert response.json["role"] == "editor"

        organization.reload()
        assert organization.is_member(added_user)
        assert not organization.is_admin(added_user)

    def test_update_member(self, api):
        user = api.login()
        updated_user = UserFactory()
        organization = OrganizationFactory(
            members=[Member(user=user, role="admin"), Member(user=updated_user, role="editor")]
        )

        api_url = url_for("api.member", org=organization, user=updated_user)
        response = api.put(api_url, {"role": "admin"})

        assert200(response)

        assert response.json["role"] == "admin"

        organization.reload()
        assert organization.is_member(updated_user)
        assert organization.is_admin(updated_user)

    def test_only_admin_can_update_member(self, api):
        user = api.login()
        updated_user = UserFactory()
        organization = OrganizationFactory(
            members=[Member(user=user, role="editor"), Member(user=updated_user, role="editor")]
        )

        api_url = url_for("api.member", org=organization, user=updated_user)
        response = api.put(api_url, {"role": "admin"})

        assert403(response)

        organization.reload()
        assert organization.is_member(updated_user)
        assert not organization.is_admin(updated_user)

    def test_delete_member(self, api):
        user = api.login()
        deleted_user = UserFactory()
        organization = OrganizationFactory(
            members=[Member(user=user, role="admin"), Member(user=deleted_user, role="editor")]
        )

        api_url = url_for("api.member", org=organization, user=deleted_user)
        response = api.delete(api_url)
        assert204(response)

        organization.reload()
        assert not organization.is_member(deleted_user)
        assert organization.get_metrics()["members"] == 1

    def test_only_admin_can_delete_member(self, api):
        user = api.login()
        deleted_user = UserFactory()
        organization = OrganizationFactory(
            members=[Member(user=user, role="editor"), Member(user=deleted_user, role="editor")]
        )

        api_url = url_for("api.member", org=organization, user=deleted_user)
        response = api.delete(api_url)
        assert403(response)

        organization.reload()
        assert organization.is_member(deleted_user)

    def test_follow_org(self, api):
        """It should follow an organization on POST"""
        user = api.login()
        to_follow = OrganizationFactory()

        url = url_for("api.organization_followers", id=to_follow.id)
        response = api.post(url)
        assert201(response)

        to_follow.count_followers()
        assert to_follow.get_metrics()["followers"] == 1

        assert Follow.objects.following(to_follow).count() == 0
        assert Follow.objects.followers(to_follow).count() == 1
        follow = Follow.objects.followers(to_follow).first()
        assert isinstance(follow.following, Organization)
        assert Follow.objects.following(user).count() == 1
        assert Follow.objects.followers(user).count() == 0

    def test_unfollow_org(self, api):
        """It should unfollow the organization on DELETE"""
        user = api.login()
        to_follow = OrganizationFactory()
        Follow.objects.create(follower=user, following=to_follow)

        url = url_for("api.organization_followers", id=to_follow.id)
        response = api.delete(url)
        assert200(response)

        nb_followers = Follow.objects.followers(to_follow).count()

        assert nb_followers == 0
        assert response.json["followers"] == nb_followers

        assert Follow.objects.following(to_follow).count() == 0
        assert Follow.objects.following(user).count() == 0
        assert Follow.objects.followers(user).count() == 0

    def test_suggest_organizations_api(self, api):
        """It should suggest organizations"""
        for i in range(3):
            OrganizationFactory(
                name="test-{0}".format(i) if i % 2 else faker.word(), metrics={"followers": i}
            )
        max_follower_organization = OrganizationFactory(name="test-4", metrics={"followers": 10})
        response = api.get(url_for("api.suggest_organizations"), qs={"q": "tes", "size": "5"})
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

    def test_suggest_organizations_with_special_chars(self, api):
        """It should suggest organizations with special caracters"""
        for i in range(4):
            OrganizationFactory(name="testé-{0}".format(i) if i % 2 else faker.word())

        response = api.get(url_for("api.suggest_organizations"), qs={"q": "testé", "size": "5"})
        assert200(response)

        assert len(response.json) <= 5
        assert len(response.json) > 1

        for suggestion in response.json:
            assert "id" in suggestion
            assert "slug" in suggestion
            assert "name" in suggestion
            assert "image_url" in suggestion
            assert "testé" in suggestion["name"]

    def test_suggest_organizations_with_multiple_words(self, api):
        """It should suggest organizations with words"""
        for i in range(4):
            OrganizationFactory(name="mon testé-{0}".format(i) if i % 2 else faker.word())

        response = api.get(url_for("api.suggest_organizations"), qs={"q": "mon testé", "size": "5"})
        assert200(response)

        assert len(response.json) <= 5
        assert len(response.json) > 1

        for suggestion in response.json:
            assert "id" in suggestion
            assert "slug" in suggestion
            assert "name" in suggestion
            assert "image_url" in suggestion
            assert "mon testé" in suggestion["name"]

    def test_suggest_organizations_with_apostrophe(self, api):
        """It should suggest organizations with words"""
        for i in range(4):
            OrganizationFactory(
                name="Ministère de l'intérieur {0}".format(i) if i % 2 else faker.word()
            )

        response = api.get(url_for("api.suggest_organizations"), qs={"q": "Ministère", "size": "5"})
        assert200(response)

        assert len(response.json) <= 5
        assert len(response.json) > 1

        for suggestion in response.json:
            assert "id" in suggestion
            assert "slug" in suggestion
            assert "name" in suggestion
            assert "image_url" in suggestion
            assert "Ministère" in suggestion["name"]

    def test_suggest_organizations_api_no_match(self, api):
        """It should not provide organization suggestion if no match"""
        OrganizationFactory.create_batch(3)

        response = api.get(url_for("api.suggest_organizations"), qs={"q": "xxxxxx", "size": "5"})
        assert200(response)
        assert len(response.json) == 0

    def test_suggest_organizations_api_empty(self, api):
        """It should not provide organization suggestion if no data"""
        response = api.get(url_for("api.suggest_organizations"), qs={"q": "xxxxxx", "size": "5"})
        assert200(response)
        assert len(response.json) == 0

    def test_suggest_organizations_homonyms(self, api):
        """It should suggest organizations and not deduplicate homonyms"""
        OrganizationFactory.create_batch(2, name="homonym")

        response = api.get(url_for("api.suggest_organizations"), qs={"q": "homonym", "size": "5"})
        assert200(response)

        assert len(response.json) == 2

        for suggestion in response.json:
            assert suggestion["name"] == "homonym"

    def test_suggest_organizations_acronym(self, api):
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
        response = api.get(url_for("api.suggest_organizations"), qs={"q": "uDaTa", "size": "5"})
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


class OrganizationDatasetsAPITest:
    modules = []

    def test_list_org_datasets(self, api):
        """Should list organization datasets"""
        org = OrganizationFactory()
        datasets = DatasetFactory.create_batch(3, organization=org)

        response = api.get(url_for("api.org_datasets", org=org))

        assert200(response)
        assert len(response.json["data"]) == len(datasets)

    def test_list_org_datasets_private(self, api):
        """Should include private datasets when member"""
        user = api.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        datasets = DatasetFactory.create_batch(3, organization=org, private=True)

        response = api.get(url_for("api.org_datasets", org=org))

        assert200(response)
        assert len(response.json["data"]) == len(datasets)

    def test_list_org_datasets_hide_private(self, api):
        """Should not include private datasets when not member"""
        org = OrganizationFactory()
        datasets = DatasetFactory.create_batch(3, organization=org)
        DatasetFactory.create_batch(2, organization=org, private=True)

        response = api.get(url_for("api.org_datasets", org=org))

        assert200(response)
        assert len(response.json["data"]) == len(datasets)

    def test_list_org_datasets_with_size(self, api):
        """Should list organization datasets"""
        org = OrganizationFactory()
        DatasetFactory.create_batch(3, organization=org)

        response = api.get(url_for("api.org_datasets", org=org), qs={"page_size": 2})

        assert200(response)
        assert len(response.json["data"]) == 2


class OrganizationReusesAPITest:
    modules = []

    def test_list_org_reuses(self, api):
        """Should list organization reuses"""
        org = OrganizationFactory()
        reuses = ReuseFactory.create_batch(3, organization=org)

        response = api.get(url_for("api.org_reuses", org=org))

        assert200(response)
        assert len(response.json) == len(reuses)

    def test_list_org_reuses_private(self, api):
        """Should include private reuses when member"""
        user = api.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        reuses = ReuseFactory.create_batch(3, organization=org, private=True)

        response = api.get(url_for("api.org_reuses", org=org))

        assert200(response)
        assert len(response.json) == len(reuses)

    def test_list_org_reuses_hide_private(self, api):
        """Should not include private reuses when not member"""
        org = OrganizationFactory()
        reuses = ReuseFactory.create_batch(3, organization=org)
        ReuseFactory.create_batch(2, organization=org, private=True)

        response = api.get(url_for("api.org_reuses", org=org))

        assert200(response)
        assert len(response.json) == len(reuses)


class OrganizationDiscussionsAPITest:
    modules = []

    def test_list_org_discussions(self, api):
        """Should list organization discussions"""
        user = UserFactory()
        org = OrganizationFactory()
        reuse = ReuseFactory(organization=org)
        dataset = DatasetFactory(organization=org)
        discussions = [
            Discussion.objects.create(subject=dataset, title="", user=user),
            Discussion.objects.create(subject=reuse, title="", user=user),
        ]

        response = api.get(url_for("api.org_discussions", org=org))

        assert200(response)
        assert len(response.json) == len(discussions)

        discussions_ids = [str(d.id) for d in discussions]
        for discussion in response.json:
            assert discussion["id"] in discussions_ids


class OrganizationBadgeAPITest:
    modules = []

    @pytest.fixture(autouse=True)
    def setUp(self, api, clean_db):
        self.factory = badge_factory(Organization)
        self.user = api.login(AdminFactory())
        self.organization = OrganizationFactory()

    def test_list(self, api):
        response = api.get(url_for("api.available_organization_badges"))
        assert200(response)
        assert len(response.json) == len(Organization.__badges__)
        for kind, label in Organization.__badges__.items():
            assert kind in response.json
            assert response.json[kind] == label

    def test_create(self, api):
        data = self.factory.as_dict()
        url = url_for("api.organization_badges", org=self.organization)
        with assert_emit(on_badge_added):
            response = api.post(url, data)
            assert201(response)
        self.organization.reload()
        assert len(self.organization.badges) == 1

    def test_create_same(self, api):
        data = self.factory.as_dict()
        url = url_for("api.organization_badges", org=self.organization)
        with assert_emit(on_badge_added):
            api.post(url, data)
        with assert_not_emit(on_badge_added):
            response = api.post(url, data)
            assert200(response)
        self.organization.reload()
        assert len(self.organization.badges) == 1

    def test_create_2nd(self, api):
        # Explicitely setting the kind to avoid collisions given the
        # small number of choices for kinds.
        kinds_keys = list(Organization.__badges__)
        self.organization.add_badge(kinds_keys[0])
        data = self.factory.as_dict()
        data["kind"] = kinds_keys[1]
        url = url_for("api.organization_badges", org=self.organization)
        response = api.post(url, data)
        assert201(response)
        self.organization.reload()
        assert len(self.organization.badges) == 2

    def test_delete(self, api):
        badge = self.factory()
        self.organization.add_badge(badge.kind)
        self.organization.save()
        url = url_for("api.organization_badge", org=self.organization, badge_kind=str(badge.kind))
        with assert_emit(on_badge_removed):
            response = api.delete(url)
            assert204(response)
        self.organization.reload()
        assert len(self.organization.badges) == 0

    def test_delete_404(self, api):
        kind = str(self.factory().kind)
        url = url_for("api.organization_badge", org=self.organization, badge_kind=kind)
        response = api.delete(url)
        assert404(response)


class OrganizationContactPointsAPITest:
    modules = []

    def test_org_contact_points(self, api):
        user = api.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        data = {
            "email": "mooneywayne@cobb-cochran.com",
            "name": "Martin Schultz",
            "organization": str(org.id),
            "role": "contact",
        }
        response = api.post(url_for("api.contact_points"), data)
        assert201(response)

        response = api.get(url_for("api.org_contact_points", org=org))
        assert200(response)

        assert response.json["data"][0]["name"] == data["name"]
        assert response.json["data"][0]["email"] == data["email"]


class OrganizationCsvExportsTest:
    modules = []

    def test_datasets_csv(self, api):
        org = OrganizationFactory()
        [DatasetFactory(organization=org, resources=[ResourceFactory()]) for _ in range(3)]

        response = api.get(url_for("api.organization_datasets_csv", org=org))

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

    def test_resources_csv(self, api):
        org = OrganizationFactory()
        datasets = [
            DatasetFactory(organization=org, resources=[ResourceFactory(), ResourceFactory()])
            for _ in range(3)
        ]
        not_org_dataset = DatasetFactory(resources=[ResourceFactory()])
        hidden_dataset = DatasetFactory(private=True)

        response = api.get(url_for("api.organization_datasets_resources_csv", org=org))

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

    def test_discussions_csv_content_empty(self, api):
        organization = OrganizationFactory()
        response = api.get(url_for("api.organization_discussions_csv", org=organization))
        assert200(response)

        assert response.data.decode("utf8") == (
            '"id";"user";"subject";"subject_class";"subject_id";"title";"size";"participants";'
            '"messages";"created";"closed";"closed_by";"closed_by_id";"closed_by_organization";'
            '"closed_by_organization_id"\r\n'
        )

    def test_discussions_csv_content_filled(self, api):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        user = UserFactory(first_name="John", last_name="Snow")
        discussion = DiscussionFactory(subject=dataset, user=user)
        response = api.get(url_for("api.organization_discussions_csv", org=organization))
        assert200(response)

        headers, data = response.data.decode("utf-8").strip().split("\r\n")
        expected = '"{discussion.id}";"{discussion.user}"'
        assert_starts_with(data, expected.format(discussion=discussion))
