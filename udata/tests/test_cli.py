# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def test_cli_help(cli):
    '''Should display help without errors'''
    cli()
    cli('-?')
    cli('-h')
    cli('--help')


def test_cli_log_and_printing(cli):
    '''Should properly log and print'''
    cli('test log')


def test_cli_version(cli):
    '''Should display version without errors'''
    cli('--version')
