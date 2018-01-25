# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

import click

from udata.commands import cli
from udata.linkchecker.tasks import check_resources


log = logging.getLogger(__name__)


@cli.group('linkchecker')
def grp():
    '''Link checking operations'''
    pass


@grp.command()
@click.option('-n', '--number', type=int, default=5000,
              help='Number of URLs to check')
def check(number):
    '''Check <number> of URLs that have not been (recently) checked'''
    check_resources(number)
