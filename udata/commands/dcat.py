import click

from rdflib import URIRef, BNode

from udata.commands import cli
from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.rdf import dataset_from_rdf
from udata.harvest.tests.factories import HarvestSourceFactory, HarvestJobFactory
from udata.harvest.backends.dcat import DcatBackend

@cli.group('dcat')
def grp():
    '''DCAT diagnosis operations'''
    pass


@grp.command()
@click.argument('url')
def parse_url(url):
    '''Parse the datasets in a DCAT format located at URL (debug)'''
    source = HarvestSourceFactory()
    source.url = url
    backend = DcatBackend(source, dryrun=True)
    job = HarvestJobFactory()
    backend.job = job
    format = backend.get_format()
    print('format:', format)
    graph = backend.parse_graph(url, format)
    print('graph', graph)
    for item in job.items:
        print(item.remote_id, item.kwargs)
        node = backend.get_node_from_item(item)
        dataset = DatasetFactory()
        dataset = dataset_from_rdf(graph, dataset, node=node)
        print('---')
        print(dataset)
        print(dataset.license)
        print(dataset.description)
        print(dataset.tags)
        print([(r.title, r.format, r.url) for r in dataset.resources])
        print('---')
