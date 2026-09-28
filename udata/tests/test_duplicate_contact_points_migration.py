import pytest
from mongoengine.connection import get_db
from mongoengine.errors import MultipleObjectsReturned
from rdflib import BNode, Graph, Literal
from rdflib.resource import Resource as RdfResource

from udata.core.contact_point.factories import ContactPointFactory
from udata.core.contact_point.models import ContactPoint
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.db import migrations
from udata.rdf import DCT, FOAF, RDF, contact_points_from_rdf
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-09-11-merge-duplicate-contact-points.py"

EMAIL = "depp-open-data@example.org"


def store(contact_point, **fields):
    """Write raw values into a contact point, as an upsert leaves them.

    An upsert stores an explicit `null` for a field it has no value for, where mongoengine
    turns a `None` into an `$unset`: the two shapes a query cannot tell apart cannot both be
    written through the model.
    """
    ContactPoint.objects(id=contact_point.id).update(__raw__={"$set": fields})


def nameless(organization, **overrides):
    fields = {"role": "rightsHolder", "name": None, "contact_form": None, "email": EMAIL}
    return ContactPointFactory(organization=organization, **{**fields, **overrides})


def contact_points_of(document):
    return document.__class__.objects.get(id=document.id).contact_points


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


def harvest(organization):
    """Harvest the nameless `foaf:Agent` of a dataset, as the DCAT catalog of the duplicates
    exposes it: an address and nothing else."""
    graph = Graph()
    agent = BNode()
    graph.add((agent, RDF.type, FOAF.Agent))
    graph.add((agent, FOAF.mbox, Literal(f"mailto:{EMAIL}")))
    dataset = BNode()
    graph.add((dataset, DCT.rightsHolder, agent))

    return list(
        contact_points_from_rdf(
            RdfResource(graph, dataset), DCT.rightsHolder, "rightsHolder", organization
        )
    )


class DuplicateContactPointsMigrationTest(PytestOnlyDBTestCase):
    @pytest.fixture(autouse=True)
    def without_the_unique_index(self):
        """The duplicates this migration removes are the reason the unique index on
        `ContactPoint` cannot exist yet: the index is deployed once they are gone, never
        before. Dropping it here sets up the state the migration actually runs in, rather
        than a state the index makes unreachable.

        Restored at the end: the test database keeps its indexes from one test to the next.
        """
        collection = ContactPoint._get_collection()
        collection.drop_indexes()
        yield
        collection.delete_many({})
        ContactPoint.ensure_indexes()

    def test_a_null_field_and_an_absent_one_are_the_same_duplicate(self):
        """The shape found in production: the contact point normalized by
        `2026-08-21-clean-nameless-contact-points` has no name at all, the one harvested
        before it ran has an explicit `null` one."""
        org = OrganizationFactory()
        kept = nameless(org)
        duplicate = nameless(org)
        store(duplicate, name=None)

        migrate()

        assert list(ContactPoint.objects) == [kept]

    def test_the_oldest_is_the_one_kept(self):
        org = OrganizationFactory()
        kept = nameless(org)
        nameless(org)
        nameless(org)

        migrate()

        assert list(ContactPoint.objects) == [kept]

    def test_harvesting_fails_on_the_duplicates_and_reuses_the_merged_one(self):
        org = OrganizationFactory()
        kept = nameless(org)
        duplicate = nameless(org)
        store(duplicate, name=None)

        with pytest.raises(MultipleObjectsReturned):
            harvest(org)

        migrate()

        assert harvest(org) == [kept]
        assert ContactPoint.objects.count() == 1

    def test_a_dataset_is_repointed_to_the_kept_contact_point(self):
        org = OrganizationFactory()
        kept = nameless(org)
        duplicate = nameless(org)
        dataset = DatasetFactory(organization=org, contact_points=[duplicate])

        migrate()

        assert contact_points_of(dataset) == [kept]

    def test_a_dataservice_is_repointed_too(self):
        org = OrganizationFactory()
        kept = nameless(org)
        duplicate = nameless(org)
        dataservice = DataserviceFactory(organization=org, contact_points=[duplicate])

        migrate()

        assert contact_points_of(dataservice) == [kept]

    def test_a_dataset_referencing_both_names_the_kept_one_once(self):
        org = OrganizationFactory()
        kept = nameless(org)
        duplicate = nameless(org)
        dataset = DatasetFactory(organization=org, contact_points=[kept, duplicate])

        migrate()

        assert contact_points_of(dataset) == [kept]

    def test_the_other_contact_points_of_a_dataset_are_kept(self):
        org = OrganizationFactory()
        kept = nameless(org)
        duplicate = nameless(org)
        other = ContactPointFactory(organization=org, role="contact")
        dataset = DatasetFactory(organization=org, contact_points=[duplicate, other])

        migrate()

        assert contact_points_of(dataset) == [other, kept]

    def test_the_same_contact_point_under_two_owners_is_not_a_duplicate(self):
        """A contact point is shared by the objects of its owner and by nobody else's:
        one per owner is the expected state, not a repetition."""
        mine = nameless(OrganizationFactory())
        theirs = nameless(OrganizationFactory())

        migrate()

        assert set(ContactPoint.objects) == {mine, theirs}

    def test_contact_points_that_differ_are_left_alone(self):
        org = OrganizationFactory()
        contact = nameless(org)
        other_role = nameless(org, role="creator")
        other_email = nameless(org, email="other@example.org")

        migrate()

        assert set(ContactPoint.objects) == {contact, other_role, other_email}
