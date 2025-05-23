from udata.forms import Form, ModelForm, fields, validators
from udata.i18n import lazy_gettext as _

from .constants import COMMENT_SIZE_LIMIT
from .models import Discussion

__all__ = ("DiscussionCreateForm", "DiscussionCommentForm")


class DiscussionCreateForm(ModelForm):
    model_class = Discussion

    organization = fields.PublishAsField(_("Publish as"), owner_field=None)
    title = fields.StringField(_("Title"), [validators.DataRequired()])
    comment = fields.StringField(
        _("Comment"), [validators.DataRequired(), validators.Length(max=COMMENT_SIZE_LIMIT)]
    )
    subject = fields.ModelField(_("Subject"), [validators.DataRequired()])
    extras = fields.ExtrasField()


class DiscussionEditForm(ModelForm):
    model_class = Discussion

    title = fields.StringField(_("Title"), [validators.DataRequired()])


class DiscussionCommentForm(Form):
    organization = fields.PublishAsField(_("Publish as"), owner_field=None)

    comment = fields.StringField(_("Comment"), [validators.Length(max=COMMENT_SIZE_LIMIT)])
    close = fields.BooleanField(default=False)


class DiscussionEditCommentForm(Form):
    comment = fields.StringField(
        _("Comment"), [validators.DataRequired(), validators.Length(max=COMMENT_SIZE_LIMIT)]
    )
