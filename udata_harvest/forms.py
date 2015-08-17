# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import Form, fields, validators
from udata.i18n import lazy_gettext as _


from .actions import list_backends

__all__ = 'HarvestSourceForm',


backends = [(b.name, b.display_name) for b in list_backends()]


class HarvestSourceForm(Form):
    name = fields.StringField(_('Nom'), [validators.required()])
    description = fields.MarkdownField(_('Description'),
        description=_('Some optionnal details about this harvester'))
    url = fields.URLField(_('URL'), [validators.required()])
    backend = fields.SelectField(_('Backend'), choices=backends)
    owner = fields.CurrentUserField()
    organization = fields.PublishAsField(_('Publish as'))
