import logging

import click
import mongoengine

from rdflib import Graph

from udata.commands import cli, green, yellow, cyan, echo, magenta
from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.rdf import dataset_from_rdf
from udata.harvest.backends.dcat import DcatBackend
from udata.rdf import namespace_manager

log = logging.getLogger(__name__)

@cli.group('dcat')
def grp():
    '''DCAT diagnosis operations'''
    pass


@grp.command()
@click.argument('url')
@click.option('-q', '--quiet', is_flag=True, help='Ignore warnings')
def parse_url(url, quiet=False):
    '''Parse the datasets in a DCAT format located at URL (debug)'''
    if quiet:
        verbose_loggers = ['rdflib', 'udata.core.dataset']
        [logging.getLogger(l).setLevel(logging.ERROR) for l in verbose_loggers]

    class MockSource:
        url = ''

    class MockJob:
        items = []

    class MockDatasetFactory(DatasetFactory):
        '''Use DatasetFactory without .save()'''
        @classmethod
        def _create(cls, model_class, *args, **kwargs):
            instance = model_class(*args, **kwargs)
            return instance

    echo(cyan('Parsing url {}'.format(url)))
    source = MockSource()
    source.url = url
    backend = DcatBackend(source, dryrun=True)
    backend.job = MockJob()
    format = backend.get_format()
    echo(yellow('Detected format: {}'.format(format)))
    graph = backend.parse_graph(url, format)

    # serialize/unserialize graph like in the job mechanism
    _graph = graph.serialize(format=format, indent=None)
    graph = Graph(namespace_manager=namespace_manager)
    graph.parse(data=_graph, format=format)

    for item in backend.job.items:
        echo(magenta('Processing item {}'.format(item.remote_id)))
        echo('Item kwargs: {}'.format(yellow(item.kwargs)))
        node = backend.get_node_from_item(item)
        dataset = MockDatasetFactory()
        dataset = dataset_from_rdf(graph, dataset, node=node)
        echo('')
        echo(green('Dataset found!'))
        echo('Title: {}'.format(yellow(dataset)))
        echo('License: {}'.format(yellow(dataset.license)))
        echo('Description: {}'.format(yellow(dataset.description)))
        echo('Tags: {}'.format(yellow(dataset.tags)))
        echo('Resources: {}'.format(yellow([(r.title, r.format, r.url) for r in dataset.resources])))

        try:
            dataset.validate()
        except mongoengine.errors.ValidationError as e:
            log.error(e, exc_info=True)
        else:
            echo(green('Dataset is valid ✅'))
        echo('')
