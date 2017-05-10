# -*- coding: utf-8 -*-
from mongoengine import signals
from udata.frontend.markdown import mdstrip


def mdstrip_field(populate_from, populate=None, length=None, end=None):

    def apply_mdstrip(sender, document, *args, **kwargs):
        to_ = populate or populate_from + '_rendered'
        if (populate_from in document._get_changed_fields() or
                getattr(document, '_created')):
            from_value = getattr(document, populate_from)
            stripped_value = mdstrip(from_value, length=length, end=end)
            document.__setattr__(to_, stripped_value)

    def decorator(cls):
        old_init = cls.__init__
        def new_init(self, *args, **kwargs):
            old_init(self, *args, **kwargs)
            signals.pre_save_post_validation.connect(apply_mdstrip,
                                                     sender=self.__class__)

        cls.__init__ = new_init

        return cls
    return decorator
