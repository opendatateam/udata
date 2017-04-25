# -*- coding: utf-8 -*-
from udata.frontend.markdown import mdstrip
from mongoengine import signals


def mdstrip_field(populate_from, populate=None, length=None, end=None):
    def func_(sender, document, *args, **kwargs):
        to_ = to_ or populate_from + '_rendered'
        from_value = getattr(document, populate_from)
        stripped_value = mdstrip(from_value, length=length, end=end)
        setattr(document, to_, stripped_value)


    def apply(cls):
        signals.post_init.connect(func_, sender=cls)
        signals.pre_save_post_validation.connect(func_, sender=cls)
        return cls
    return apply
