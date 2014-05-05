# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from blinker import Signal
from mongoengine.signals import post_save

from udata.models import db


__all__ = ('Activity', )


class EmitNewActivityMetaClass(db.BaseDocumentMetaclass):
    '''Ensure any child class dispatch the on_new signal'''
    def __new__(cls, name, bases, attrs):
        new_class = super(EmitNewActivityMetaClass, cls).__new__(cls, name, bases, attrs)
        post_save.connect(cls.post_save, sender=new_class)
        return new_class

    @classmethod
    def post_save(cls, sender, document, **kwargs):
        sender.on_new.send(sender, activity=document)


class Activity(db.Document):
    '''Store the activity entries for a single related object'''
    actor = db.ReferenceField('User', required=True)
    as_organization = db.ReferenceField('Organization')
    created_at = db.DateTimeField(default=datetime.now, required=True)

    on_new = Signal()

    __metaclass__ = EmitNewActivityMetaClass

    meta = {
        'indexes': [
            'actor',
            'as_organization',
            '-created_at',
            ('actor', '-created_at'),
            ('as_organization', '-created_at'),
        ],
        'allow_inheritance': True,
    }

    @classmethod
    def connect(cls, func):
        return cls.on_new.connect(func, sender=cls)
