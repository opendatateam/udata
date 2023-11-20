from udata.forms import ModelForm, fields, validators
from udata.i18n import lazy_gettext as _
from udata.models import ContactPoint


__all__ = ('ContactPointForm',)


class ContactPointForm(ModelForm):
    model_class = ContactPoint

    name = fields.StringField(_('Name'), [validators.DataRequired(),
                                                validators.NoURLs(_('URLs not allowed in this field'))])
    email = fields.StringField(_('Email'), [validators.DataRequired(), validators.Email()])
    owner = fields.CurrentUserField()
    organization = fields.PublishAsField(_('Publish as'))
