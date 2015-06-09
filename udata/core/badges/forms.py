# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import Form, fields, validators
from udata.i18n import lazy_gettext as _

from .models import BADGE_KINDS

__all__ = ('BadgeCreateForm',)


class BadgeCreateForm(Form):
    subject = fields.DatasetOrOrganizationField(
        _('Subject'), [validators.required()])
    kind = fields.RadioField(
        _('Kind'), [validators.required()],
        choices=BADGE_KINDS.items(),
        description=_('The kind of badge you want to create.'))
