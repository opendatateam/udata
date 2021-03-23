from udata.forms import ModelForm, Form, fields, validators
from udata.i18n import lazy_gettext as _

from .models import Discussion, COMMENT_SIZE_LIMIT

__all__ = ('DiscussionCreateForm', 'DiscussionCommentForm')


class DiscussionCreateForm(ModelForm):
    model_class = Discussion

    title = fields.StringField(_('Title'), [validators.DataRequired()])
    comment = fields.StringField(
        _('Comment'), [validators.DataRequired(), validators.Length(max=COMMENT_SIZE_LIMIT)])
    subject = fields.ModelField(_('Subject'), [validators.DataRequired()])
    extras = fields.ExtrasField()


class DiscussionCommentForm(Form):
    comment = fields.StringField(
        _('Comment'), [validators.DataRequired(), validators.Length(max=COMMENT_SIZE_LIMIT)])
    close = fields.BooleanField(default=False)
