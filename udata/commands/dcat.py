import logging

import click
import mongoengine
from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from udata.commands import cli, cyan, echo, green, magenta, yellow
from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.rdf import dataset_from_rdf
from udata.harvest.backends.dcat import (
    CswDcatBackend,
    CswIso19139DcatBackend,
    DcatBackend,
)
from udata.harvest.models import HarvestItem
from udata.rdf import DCAT, DCT, namespace_manager

log = logging.getLogger(__name__)


@cli.group("dcat")
def grp():
    """DCAT diagnosis operations"""
    pass


@grp.command()
@click.argument("url")
@click.option("-q", "--quiet", is_flag=True, help="Ignore warnings")
@click.option("-r", "--rid", help="Inspect specific remote id (contains)")
@click.option("-c", "--csw", is_flag=True, help="The target is a CSW endpoint with DCAT output")
@click.option("-i", "--iso", is_flag=True, help="The target is a CSW endpoint with ISO output")
def parse_url(url, csw, iso, quiet=False, rid=""):
    """Parse the datasets in a DCAT format located at URL (debug)"""
    if quiet:
        verbose_loggers = ["rdflib", "udata.core.dataset"]
        [logging.getLogger(logger).setLevel(logging.ERROR) for logger in verbose_loggers]

    class MockSource:
        url = ""

    class MockJob:
        items = []

    class MockDatasetFactory(DatasetFactory):
        """Use DatasetFactory without .save()"""

        @classmethod
        def _create(cls, model_class, *args, **kwargs):
            instance = model_class(*args, **kwargs)
            return instance

    echo(cyan("Parsing url {}".format(url)))
    source = MockSource()
    source.url = url
    if csw:
        backend = CswDcatBackend(source, dryrun=True)
    elif iso:
        backend = CswIso19139DcatBackend(source, dryrun=True)
    else:
        backend = DcatBackend(source, dryrun=True)
    backend.job = MockJob()
    format = backend.get_format()
    echo(yellow("Detected format: {}".format(format)))
    graphs = backend.walk_graph(url, format)

    # serialize/unserialize graph like in the job mechanism
    graph = Graph(namespace_manager=namespace_manager)
    for page_number, subgraph in graphs:
        serialized = subgraph.serialize(format=format, indent=None)
        _subgraph = Graph(namespace_manager=namespace_manager)
        graph += _subgraph.parse(data=serialized, format=format)

        for node in subgraph.subjects(RDF.type, DCAT.Dataset):
            identifier = subgraph.value(node, DCT.identifier)
            kwargs = {"nid": str(node), "page": page_number}
            kwargs["type"] = "uriref" if isinstance(node, URIRef) else "blank"
            item = HarvestItem(remote_id=str(identifier), kwargs=kwargs)
            backend.job.items.append(item)

    for item in backend.job.items:
        if not rid or rid in item.remote_id:
            echo(magenta("Processing item {}".format(item.remote_id)))
            echo("Item kwargs: {}".format(yellow(item.kwargs)))
            node = backend.get_node_from_item(graph, item)
            dataset = MockDatasetFactory()
            dataset = dataset_from_rdf(graph, dataset, node=node)
            echo("")
            echo(green("Dataset found!"))
            echo("Title: {}".format(yellow(dataset)))
            echo("License: {}".format(yellow(dataset.license)))
            echo("Description: {}".format(yellow(dataset.description)))
            echo("Tags: {}".format(yellow(dataset.tags)))
            echo(
                "Resources: {}".format(
                    yellow([(r.title, r.format, r.url) for r in dataset.resources])
                )
            )

            try:
                dataset.validate()
            except mongoengine.errors.ValidationError as e:
                log.error(e, exc_info=True)
            else:
                echo(green("Dataset is valid ✅"))
            echo("")
