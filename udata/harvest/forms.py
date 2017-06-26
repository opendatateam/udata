# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import Form, fields, validators
from udata.i18n import lazy_gettext as _


from .actions import list_backends
from .models import VALIDATION_STATES, VALIDATION_REFUSED

__all__ = 'HarvestSourceForm', 'HarvestSourceValidationForm'


class HarvestSourceForm(Form):
    name = fields.StringField(_('Name'), [validators.required()])
    description = fields.MarkdownField(
        _('Description'),
        description=_('Some optionnal details about this harvester'))
    url = fields.URLField(_('URL'), [validators.required()])
    backend = fields.SelectField(_('Backend'), choices=lambda: [
        (b.name, b.display_name) for b in list_backends()
    ])
    owner = fields.CurrentUserField()
    organization = fields.PublishAsField(_('Publish as'))


class HarvestSourceValidationForm(Form):
    state = fields.SelectField(choices=VALIDATION_STATES.items())
    comment = fields.StringField(_('Comment'),
                                 [validators.RequiredIfVal('state',
                                                           VALIDATION_REFUSED
                                                           )])
