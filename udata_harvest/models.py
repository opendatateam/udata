# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ConfigParser import ConfigParser
from datetime import datetime

from udata.models import db


def cast(config, section):
    return dict((k, True if v == 'true' else v) for k, v in config.items(section))


class Job(db.EmbeddedDocument):
    '''Keep track of harvestings'''
    created_at = db.DateTimeField(default=datetime.now, required=True)
    started_at = db.DateTimeField()
    finished_at = db.DateTimeField()
    status = db.StringField()
    errors = db.ListField(db.StringField)


class Harvester(db.Document):
    name = db.StringField(unique=True)
    description = db.StringField()
    backend = db.StringField()
    jobs = db.ListField(db.EmbeddedDocumentField(Job))
    config = db.DictField()
    mapping = db.DictField()

    @classmethod
    def from_file(cls, filename):
        config = ConfigParser()
        config.read(filename)
        name = config.get('harvester', 'name')

        harvester, _ = cls.objects.get_or_create(name=name)
        harvester.backend = config.get('harvester', 'backend')
        harvester.description = config.get('harvester', 'description')
        if config.has_section('config'):
            harvester.config = cast(config, 'config')
        for section in config.sections():
            if section.startswith('config:'):
                name = section.split(':')[1]
                harvester.config[name] = cast(config, section)
            if section.startswith('mapping:'):
                name = section.split(':')[1]
                harvester.mapping[name] = dict(config.items(section))
        harvester.save()
        return harvester


class HarvestReference(db.EmbeddedDocument):
    remote_id = db.StringField()
    harvester = db.ReferenceField(Harvester)
    last_update = db.DateTimeField(default=datetime.now)
