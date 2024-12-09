from datetime import datetime

import pytest

import udata.core.organization.constants as org_constants
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.factories import DatasetFactory, HiddenDatasetFactory
from udata.core.followers.signals import on_follow, on_unfollow
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Organization, OrganizationBadge
from udata.core.reuse.factories import ReuseFactory, VisibleReuseFactory
from udata.core.user.factories import UserFactory
from udata.models import Dataset, Follow, Member, Reuse, db
from udata.tests.helpers import assert_emit

from .. import DBTestMixin, TestCase


class OrganizationModelTest(TestCase, DBTestMixin):
    # Load metrics
    import udata.core.organization.metrics  # noqa
    import udata.core.followers.metrics  # noqa

    def test_organization_metrics(self):
        # Members count update are in API calls, thus being tested in API dedicated tests

        member = Member(user=UserFactory(), role="admin")
        org = OrganizationFactory(members=[member])

        with assert_emit(Reuse.on_create):
            reuse = VisibleReuseFactory(organization=org)
            ReuseFactory(organization=org)
        with assert_emit(Dataservice.on_create):
            dataservice = DataserviceFactory(organization=org)
        with assert_emit(Dataset.on_create):
            dataset = DatasetFactory(organization=org)
            HiddenDatasetFactory(organization=org)
        with assert_emit(on_follow):
            follow = Follow.objects.create(
                following=org, follower=UserFactory(), since=datetime.utcnow()
            )

        assert org.get_metrics()["datasets"] == 1
        assert org.get_metrics()["reuses"] == 1
        assert org.get_metrics()["dataservices"] == 1
        assert org.get_metrics()["followers"] == 1

        with assert_emit(Reuse.on_delete):
            reuse.deleted = datetime.utcnow()
            reuse.save()
        with assert_emit(Dataservice.on_delete):
            dataservice.deleted_at = datetime.utcnow()
            dataservice.save()
        with assert_emit(Dataset.on_delete):
            dataset.deleted = datetime.utcnow()
            dataset.save()
        with assert_emit(on_unfollow):
            follow.until = datetime.utcnow()
            follow.save()

        assert org.get_metrics()["datasets"] == 0
        assert org.get_metrics()["reuses"] == 0
        assert org.get_metrics()["dataservices"] == 0
        assert org.get_metrics()["followers"] == 0

    def test_organization_queryset_with_badge(self):
        org_public_service = OrganizationFactory()
        org_public_service.add_badge(org_constants.PUBLIC_SERVICE)
        org_certified_association = OrganizationFactory()
        org_certified_association.add_badge(org_constants.CERTIFIED)
        org_certified_association.add_badge(org_constants.ASSOCIATION)

        public_services = list(Organization.objects.with_badge(org_constants.PUBLIC_SERVICE))
        assert len(public_services) == 1
        assert org_public_service in public_services

        certified = list(Organization.objects.with_badge(org_constants.CERTIFIED))
        assert len(certified) == 1
        assert org_certified_association in certified

        associations = list(Organization.objects.with_badge(org_constants.ASSOCIATION))
        assert len(associations) == 1
        assert org_certified_association in associations

    def test_organization__url(self):
        with pytest.raises(db.ValidationError):
            OrganizationFactory(url="not-an-url")


class OrganizationBadgeTest(DBTestMixin, TestCase):
    # Model badges can be extended in plugins, for example in udata-front
    # for french only badges.
    Organization.__badges__["new"] = "new"

    def test_validation(self):
        """It should validate default badges as well as extended ones"""
        badge = OrganizationBadge(kind="public-service")
        badge.validate()

        badge = OrganizationBadge(kind="new")
        badge.validate()

        with self.assertRaises(db.ValidationError):
            badge = OrganizationBadge(kind="doesnotexist")
            badge.validate()
