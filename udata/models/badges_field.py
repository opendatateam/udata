import logging

from mongoengine.fields import ListField, StringField

log = logging.getLogger(__name__)


class BadgesField(ListField):
    def __init__(self, **kwargs):
        self.registered = {}
        super(BadgesField, self).__init__(StringField(), **kwargs)

    def register(self, key, badge):
        self.registered[key] = badge

    def validate(self, value):
        super(BadgesField, self).validate(value)

        errors = {}

        for key in value:
            if key not in self.registered:
                errors[key] = 'Badge {0} is not registered'.format(key)

        if errors:
            self.error('Unknown badges types', errors=errors)

    def __call__(self, key):
        def inner(cls):
            self.register(key, cls)
            return cls
        return inner


class Badge(object):
    key = None
    label = None
    details = None
    admin_only = False
    visible = True

    def should_have(self, obj):
        raise NotImplementedError
