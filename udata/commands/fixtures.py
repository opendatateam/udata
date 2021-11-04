import logging
import yaml
import sys

import click
from flask import current_app

from udata.commands import cli
from udata.core.dataset.commands import frequency_reminder
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.discussions.factories import DiscussionFactory
from udata.core.discussions.models import Message, Discussion
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member, Organization
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import UserFactory

log = logging.getLogger(__name__)


@cli.command()
def generate_fixtures():
    '''Build sample fixture data (users, datasets and reuses).'''
    try:
        fictures_path = current_app.config['FIXTURES_ROOT']
    except KeyError:
        raise click.ClickException('FIXTURES_ROOT setting not set.')
    try:
        stream = open(fictures_path, 'r')
        dictionary = yaml.load(stream, Loader=yaml.FullLoader)
    except FileNotFoundError:
        raise click.FileError(fictures_path, 'File not found.')

    for fixture in dictionary:
        user = UserFactory()
        org = OrganizationFactory(**fixture['organization'], members=[Member(user=user)])
        dataset = DatasetFactory(**fixture['dataset'], organization=org)
        for resource in fixture['resources']:
            res = ResourceFactory(**resource)
            dataset.add_resource(res)
            # for discussion in data['discussions']:
            #     user = UserFactory()
            #     messages = []
            #     for message in discussion['messages']:
            #         message = Message(content=message['content'], posted_by=user)
            #     discussion = DiscussionFactory(
            #         subject=dataset,
            #         user=user,
            #         title=discussion['title'],
            #         discussion=messages)
    # log.info('Generated organization "{org.name}".'.format(org=organization))
        # ReuseFactory.create_batch(reuses, datasets=[dataset], owner=user)
