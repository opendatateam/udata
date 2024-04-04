from udata.utils import safe_unicode
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

    def get_filter_specs(self, backend, key):
        candidates = (f for f in backend.filters if f.key == key)
        return next(candidates, None)

    def get_feature_specs(self, backend, key):
        candidates = (f for f in backend.features if f.key == key)
        return next(candidates, None)

    def pre_validate(self, form):
        if self.data:
            backend = self.get_backend(form)
            # Validate filters
            for f in (self.data.get('filters') or []):
                if not ('key' in f and 'value' in f):
                    msg = 'A field should have both key and value properties'
                    raise validators.ValidationError(msg)
                specs = self.get_filter_specs(backend, f['key'])
                if not specs:
                    msg = 'Unknown filter key "{0}" for "{1}" backend'
                    msg = msg.format(f['key'], backend.name)
                    raise validators.ValidationError(msg)

                if isinstance(f['value'], str):
                    f['value'] = safe_unicode(f['value'])  # Fix encoding error

                if not isinstance(f['value'], specs.type):
                    msg = '"{0}" filter should of type "{1}"'
                    msg = msg.format(specs.key, specs.type.__name__)
                    raise validators.ValidationError(msg)
            # Validate features
            for key, value in (self.data.get('features') or {}).items():
                if not isinstance(value, bool):
                    msg = 'A feature should be a boolean'
                    raise validators.ValidationError(msg)
                if not self.get_feature_specs(backend, key):
                    msg = 'Unknown feature "{0}" for "{1}" backend'
                    msg = msg.format(key, backend.name)
                    raise validators.ValidationError(msg)


class HarvestSourceForm(Form):
    name = fields.StringField(_('Name'), [validators.DataRequired()])
    description = fields.MarkdownField(
        _('Description'),
        description=_('Some optional details about this harvester'))
    url = fields.URLField(_('URL'), [validators.DataRequired()])
    backend = fields.SelectField(_('Backend'), choices=lambda: [
        (b.name, b.display_name) for b in list_backends()
    ])
    owner = fields.CurrentUserField()
    organization = fields.PublishAsField(_('Publish as'))
    active = fields.BooleanField()
    autoarchive = fields.BooleanField()

    config = HarvestConfigField()


class HarvestSourceValidationForm(Form):
    state = fields.SelectField(choices=list(VALIDATION_STATES.items()))
    comment = fields.StringField(_('Comment'),
                                 [validators.RequiredIfVal('state',
                                                           VALIDATION_REFUSED
                                                           )])
