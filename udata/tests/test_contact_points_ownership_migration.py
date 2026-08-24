from mongoengine.connection import get_db

from udata.core.contact_point.factories import ContactPointFactory
from udata.core.contact_point.models import ContactPoint
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.db import migrations
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-08-18-fix-contact-points-ownership.py"


def point_at(document, contact_point):
    """Make `document` reference a contact point its owner does not own.

    Written straight to the collection: this is the state transfers used to leave behind, and
    the models now reject it, so no factory can build it.
    """
    document.__class__.objects(id=document.id).update(contact_points=[contact_point.id])


def contact_points_of(document):
    return document.__class__.objects.get(id=document.id).contact_points


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


class ContactPointsOwnershipMigrationTest(PytestOnlyDBTestCase):
    def test_dataset_of_an_organization_gets_a_contact_point_of_its_own(self):
        org = OrganizationFactory()
        stranger = ContactPointFactory(organization=OrganizationFactory(), role="contact")
        dataset = DatasetFactory(organization=org)
        point_at(dataset, stranger)

        migrate()

        fixed = contact_points_of(dataset)[0]
        assert fixed.organization == org
        assert fixed.owner is None
        assert (fixed.name, fixed.email, fixed.role) == (
            stranger.name,
            stranger.email,
            stranger.role,
        )

    def test_dataset_of_a_user_gets_a_contact_point_of_its_own(self):
        owner = UserFactory()
        stranger = ContactPointFactory(owner=UserFactory(), role="contact")
        dataset = DatasetFactory(owner=owner)
        point_at(dataset, stranger)

        migrate()

        fixed = contact_points_of(dataset)[0]
        assert fixed.owner == owner
        assert fixed.organization is None

    def test_dataservice_is_fixed_too(self):
        org = OrganizationFactory()
        stranger = ContactPointFactory(organization=OrganizationFactory(), role="contact")
        dataservice = DataserviceFactory(organization=org)
        point_at(dataservice, stranger)

        migrate()

        assert contact_points_of(dataservice)[0].organization == org

    def test_the_contact_point_is_left_to_whoever_owns_it(self):
        """It is shared, so the objects already using it must keep it untouched."""
        stranger_org = OrganizationFactory()
        stranger = ContactPointFactory(organization=stranger_org, role="contact")
        dataset = DatasetFactory(organization=OrganizationFactory())
        point_at(dataset, stranger)

        migrate()

        stranger.reload()
        assert stranger.organization == stranger_org

    def test_an_existing_contact_point_of_the_owner_is_reused(self):
        org = OrganizationFactory()
        stranger = ContactPointFactory(organization=OrganizationFactory(), role="contact")
        already_there = ContactPointFactory(
            organization=org,
            name=stranger.name,
            email=stranger.email,
            contact_form=stranger.contact_form,
            role=stranger.role,
        )
        dataset = DatasetFactory(organization=org)
        point_at(dataset, stranger)

        migrate()

        assert contact_points_of(dataset) == [already_there]
        assert ContactPoint.objects.count() == 2

    def test_a_consistent_object_is_left_alone(self):
        org = OrganizationFactory()
        contact_point = ContactPointFactory(organization=org, role="contact")
        dataset = DatasetFactory(organization=org, contact_points=[contact_point])

        migrate()

        assert contact_points_of(dataset) == [contact_point]
        assert ContactPoint.objects.count() == 1

    def test_an_ownerless_object_is_left_for_a_human(self):
        """Transfers do not produce those, so the migration reports them instead of guessing."""
        stranger = ContactPointFactory(organization=OrganizationFactory(), role="contact")
        ownerless = DatasetFactory()
        point_at(ownerless, stranger)

        migrate()

        assert contact_points_of(ownerless) == [stranger]

    def test_a_document_that_cannot_be_saved_does_not_stop_the_others(self):
        """A legacy contact point can fail validation; the rest must still be fixed."""
        broken = ContactPointFactory(organization=OrganizationFactory(), role="contact")
        ContactPoint.objects(id=broken.id).update(unset__name=True)
        doomed = DatasetFactory(organization=OrganizationFactory())
        point_at(doomed, broken)

        org = OrganizationFactory()
        stranger = ContactPointFactory(organization=OrganizationFactory(), role="contact")
        fixable = DatasetFactory(organization=org)
        point_at(fixable, stranger)

        migrate()

        assert contact_points_of(fixable)[0].organization == org
        assert contact_points_of(doomed) == [broken]
