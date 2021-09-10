import click

from rdflib import URIRef, BNode

from udata.commands import cli, green, yellow, cyan, echo, magenta
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
    echo(cyan('Parsing url {}'.format(url)))
    source = HarvestSourceFactory()
    source.url = url
    backend = DcatBackend(source, dryrun=True)
    job = HarvestJobFactory()
    backend.job = job
    format = backend.get_format()
    echo(yellow('Detected format: {}'.format(format)))
    graph = backend.parse_graph(url, format)
    for item in job.items:
        echo(magenta('Processing item {}'.format(item.remote_id)))
        echo('Item kwargs: {}'.format(yellow(item.kwargs)))
        node = backend.get_node_from_item(item)
        dataset = DatasetFactory()
        dataset = dataset_from_rdf(graph, dataset, node=node)
        echo('')
        echo(green('Dataset found!'))
        echo('Title: {}'.format(yellow(dataset)))
        echo('License: {}'.format(yellow(dataset.license)))
        echo('Description: {}'.format(yellow(dataset.description)))
        echo('Tags: {}'.format(yellow(dataset.tags)))
        echo('Resources: {}'.format(yellow([(r.title, r.format, r.url) for r in dataset.resources])))
        echo('')
