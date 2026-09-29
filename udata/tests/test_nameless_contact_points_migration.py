from mongoengine.connection import get_db
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

MIGRATION = "2026-08-21-clean-nameless-contact-points.py"


def strip(contact_point, **fields):
    """Empty the given fields of a contact point, as harvesting used to leave them.

    Written as a raw `$set`: an empty name is precisely what the model now refuses to say,
    and mongoengine turns a `None` into an `$unset` rather than storing it.
    """
    ContactPoint.objects(id=contact_point.id).update(__raw__={"$set": fields})


def contact_points_of(document):
    return document.__class__.objects.get(id=document.id).contact_points


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


def harvest(organization, name, mbox):
    """Harvest a `foaf:Agent` as a rights holder of a dataset, as a DCAT catalog exposes one."""
    graph = Graph()
    agent = BNode()
    graph.add((agent, RDF.type, FOAF.Agent))
    graph.add((agent, FOAF.name, Literal(name)))
    graph.add((agent, FOAF.mbox, Literal(mbox)))
    dataset = BNode()
    graph.add((dataset, DCT.rightsHolder, agent))

    return list(
        contact_points_from_rdf(
            RdfResource(graph, dataset), DCT.rightsHolder, "rightsHolder", organization
        )
    )


class NamelessContactPointsMigrationTest(PytestOnlyDBTestCase):
    def test_an_empty_name_becomes_no_name(self):
        contact_point = ContactPointFactory(organization=OrganizationFactory(), role="contact")
        strip(contact_point, name="")

        migrate()

        contact_point.reload()
        assert contact_point.name is None
        assert contact_point.email

    def test_an_empty_email_becomes_no_email(self):
        contact_point = ContactPointFactory(organization=OrganizationFactory(), role="creator")
        strip(contact_point, email="")

        migrate()

        contact_point.reload()
        assert contact_point.email is None
        assert contact_point.name

    def test_a_normalized_contact_point_is_reused_by_harvesting(self):
        """Why the empty emails are normalized: harvesting looks a contact point up by its exact
        fields before creating one, and an empty string never matches the absent value it now
        extracts from a bare `mailto:`."""
        org = OrganizationFactory()
        harvested = ContactPointFactory(
            organization=org, role="rightsHolder", name="MNHN", contact_form=None
        )
        strip(harvested, email="")

        migrate()

        assert harvest(org, name="MNHN", mbox="mailto:") == [harvested]
        assert ContactPoint.objects.count() == 1

    def test_a_contact_point_nobody_can_reach_is_removed(self):
        org = OrganizationFactory()
        unreachable = ContactPointFactory(organization=org, role="creator")
        strip(unreachable, name="", email=None, contact_form=None)
        dataset = DatasetFactory(organization=org, contact_points=[unreachable])

        migrate()

        assert contact_points_of(dataset) == []
        assert ContactPoint.objects.count() == 0

    def test_a_dataservice_is_cleaned_too(self):
        org = OrganizationFactory()
        unreachable = ContactPointFactory(organization=org, role="creator")
        strip(unreachable, name="", email=None, contact_form=None)
        dataservice = DataserviceFactory(organization=org, contact_points=[unreachable])

        migrate()

        assert contact_points_of(dataservice) == []

    def test_the_other_contact_points_of_a_dataset_are_kept(self):
        org = OrganizationFactory()
        unreachable = ContactPointFactory(organization=org, role="creator")
        strip(unreachable, name="", email=None, contact_form=None)
        kept = ContactPointFactory(organization=org, role="contact")
        dataset = DatasetFactory(organization=org, contact_points=[unreachable, kept])

        migrate()

        assert contact_points_of(dataset) == [kept]

    def test_a_nameless_contact_point_with_an_email_is_kept(self):
        """It has no name but it can still be reached, and the front falls back to the email."""
        org = OrganizationFactory()
        contact_point = ContactPointFactory(organization=org, role="creator")
        strip(contact_point, name="", contact_form=None)
        dataset = DatasetFactory(organization=org, contact_points=[contact_point])

        migrate()

        assert contact_points_of(dataset) == [contact_point]
        contact_point.reload()
        assert contact_point.name is None

    def test_a_named_contact_point_is_left_alone(self):
        org = OrganizationFactory()
        contact_point = ContactPointFactory(organization=org, role="contact")
        dataset = DatasetFactory(organization=org, contact_points=[contact_point])
        name = contact_point.name

        migrate()

        assert contact_points_of(dataset) == [contact_point]
        contact_point.reload()
        assert contact_point.name == name
