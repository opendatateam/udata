import logging
import json
import yaml
import sys

import click
import requests
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


DEFAULT_FIXTURE_FILE = ''  # noqa


@cli.command()
@click.argument('source', default=DEFAULT_FIXTURE_FILE)
def generate_fixtures(source):
    '''Build sample fixture data (users, datasets, reuses and discussions).'''
    if source.startswith('http'):
        json_fixtures = requests.get(source).json()
    else:
        with open(source) as f:
            json_fixtures = json.load(f)

    for fixture in json_fixtures:
        user = UserFactory()
        org = OrganizationFactory(**fixture['organization'], members=[Member(user=user)])
        dataset = DatasetFactory(**fixture['dataset'], organization=org)
        for resource in fixture['resources']:
            res = ResourceFactory(**resource)
            dataset.add_resource(res)
        for reuse in fixture['reuses']:
            ReuseFactory(**reuse, datasets=[dataset], owner=user)
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
