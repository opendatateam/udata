# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import Form, fields, validators
from udata.i18n import lazy_gettext as _


from .actions import list_backends
from .models import VALIDATION_STATES, VALIDATION_REFUSED

__all__ = 'HarvestSourceForm', 'HarvestSourceValidationForm'


class HarvestConfigField(fields.DictField):
    '''
    A DictField with extras validations on known configurations
    '''
    def get_backend(self, form):
        return next(b for b in list_backends() if b.name == form.backend.data)

    def get_specs(self, backend, key):
        candidates = (f for f in backend.filters if f.key == key)
        return next(candidates, None)

    def pre_validate(self, form):
        if self.data:
            backend = self.get_backend(form)
            # Validate filters
            for f in (self.data.get('filters') or []):
                if not ('key' in f and 'value' in f):
                    msg = 'A field should have both key and value properties'
                    raise validators.ValidationError(msg)
                specs = self.get_specs(backend, f['key'])
                if not specs:
                    msg = 'Unknown filter key "{0}" for "{1}" backend'
                    msg = msg.format(f['key'], backend.name)
                    raise validators.ValidationError(msg)
                if not isinstance(f['value'], specs.type):
                    msg = '"{0}" filter should of type "{1}"'
                    msg = msg.format(specs.key, specs.type.__name__)
                    raise validators.ValidationError(msg)


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

    config = HarvestConfigField()


class HarvestSourceValidationForm(Form):
    state = fields.SelectField(choices=VALIDATION_STATES.items())
    comment = fields.StringField(_('Comment'),
                                 [validators.RequiredIfVal('state',
                                                           VALIDATION_REFUSED
                                                           )])
