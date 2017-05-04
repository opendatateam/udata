# -*- coding: utf-8 -*-
from udata.frontend.markdown import mdstrip
from mongoengine import signals


def mdstrip_field(populate_from, populate=None, length=None, end=None):

    def func_(sender, document, *args, **kwargs):
        to_ = populate or populate_from + '_rendered'
        print document._get_changed_fields()
        print document._created
        if populate_from in document._get_changed_fields() or getattr(document, '_created'):
            from_value = getattr(document, populate_from)
            stripped_value = mdstrip(from_value, length=length, end=end)
            document.__setattr__(to_, stripped_value)

    def apply(cls):
        signals.pre_save_post_validation.connect(func_, sender=cls)
        return cls
    func_.apply = apply
    return func_.apply
