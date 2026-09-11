import pytest
from mongoengine.errors import NotUniqueError
from pymongo.errors import OperationFailure

from udata.core.contact_point.factories import ContactPointFactory
from udata.core.contact_point.models import ContactPoint
from udata.core.organization.factories import OrganizationFactory
from udata.tests.api import PytestOnlyDBTestCase

NAMELESS = {"role": "rightsHolder", "name": None, "contact_form": None, "email": "a@example.org"}


class UniqueContactPointIndexTest(PytestOnlyDBTestCase):
    def test_the_same_contact_point_cannot_be_written_twice(self):
        org = OrganizationFactory()
        ContactPointFactory(organization=org, **NAMELESS)

        with pytest.raises(NotUniqueError):
            ContactPointFactory(organization=org, **NAMELESS)

    def test_an_explicit_null_does_not_double_an_absent_field(self):
        """The shape the production duplicates had: mongoengine stores nothing for a `None`
        where an upsert stores a `null`, and a query cannot tell the two apart."""
        org = OrganizationFactory()
        ContactPointFactory(organization=org, **NAMELESS)

        with pytest.raises(OperationFailure) as error:
            ContactPoint._get_collection().insert_one(
                {**NAMELESS, "owner": None, "organization": org.id}
            )

        assert "E11000" in str(error.value)

    def test_a_bulk_rewrite_that_would_merge_two_contact_points_is_refused(self):
        """How the duplicates were made: normalizing an empty value into an absent one turns
        two distinct contact points into the same one. The index refuses the rewrite instead
        of leaving a pair behind, and the pair is left as it was."""
        org = OrganizationFactory()
        absent = ContactPointFactory(
            organization=org, email=None, name="DREAL", contact_form=None, role="rightsHolder"
        )
        empty = ContactPointFactory(
            organization=org,
            email="a@example.org",
            name="DREAL",
            contact_form=None,
            role="rightsHolder",
        )
        ContactPoint.objects(id=empty.id).update(__raw__={"$set": {"email": ""}})

        with pytest.raises(OperationFailure) as error:
            ContactPoint._get_collection().update_many({"email": ""}, {"$unset": {"email": ""}})

        assert "E11000" in str(error.value)
        assert {c.id for c in ContactPoint.objects} == {absent.id, empty.id}

    def test_the_same_values_under_another_owner_are_a_different_contact_point(self):
        mine = ContactPointFactory(organization=OrganizationFactory(), **NAMELESS)
        theirs = ContactPointFactory(organization=OrganizationFactory(), **NAMELESS)

        assert {c.id for c in ContactPoint.objects} == {mine.id, theirs.id}
