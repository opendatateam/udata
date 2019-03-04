from udata.forms import Form, ModelForm, fields, validators
from udata.i18n import lazy_gettext as _

from .models import Issue

__all__ = ('IssueCreateForm', 'IssueCommentForm')


class IssueCreateForm(ModelForm):
    model_class = Issue

    title = fields.StringField(_('Title'), [validators.DataRequired()])
    comment = fields.StringField(_('Comment'), [validators.DataRequired()])
    subject = fields.ModelField(_('Subject'), [validators.DataRequired()])


class IssueCommentForm(Form):
    comment = fields.StringField(_('Comment'), [validators.DataRequired()])
    close = fields.BooleanField(default=False)
