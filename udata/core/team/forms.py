from udata.forms import ModelForm, fields, validators
from udata.i18n import lazy_gettext as _

from .models import (
    TITLE_SIZE_LIMIT, DESCRIPTION_SIZE_LIMIT
)

__all__ = (
    'TeamForm'
)


class TeamForm(ModelForm):
    name = fields.StringField(_('Name'), [validators.DataRequired(), validators.Length(max=TITLE_SIZE_LIMIT)])
    description = fields.MarkdownField(
        _('Description'), [validators.DataRequired(), validators.Length(max=DESCRIPTION_SIZE_LIMIT)],
        description=_('The details about your team'))
