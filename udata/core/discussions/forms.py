from udata.forms import Form, ModelForm, fields, validators
from udata.i18n import lazy_gettext as _

from .constants import COMMENT_SIZE_LIMIT
from .models import Discussion, is_valid_notification_model_name

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

    def validate(self, extra_validators=None):
        # `external_url` is validated by `NotificationExtra` registered on
        # `Discussion.extras` (called from `super().validate()`). The per-class
        # `model_name` check stays here because it needs the discussion's
        # subject — not reachable from inside an EmbeddedDocument validator.
        ok = super().validate(extra_validators=extra_validators)
        subject = self.subject.data
        model_name = ((self.extras.data or {}).get("notification") or {}).get("model_name")
        if model_name is None or is_valid_notification_model_name(subject, model_name):
            return ok

        subject_cls = type(subject).__name__ if subject is not None else "<unknown>"
        error = _(
            "notification.model_name %(name)s is not allowed for subject type %(type)s",
            name=model_name,
            type=subject_cls,
        )
        # `ExtrasField.errors` can be a list (process errors, single mongo
        # message), a dict (per-key field errors or mongoengine error dict),
        # or None. Merge into the existing shape so an earlier failure
        # (e.g. a bad `external_url`) is not silently dropped.
        if isinstance(self.extras.errors, dict):
            self.extras.errors["notification.model_name"] = str(error)
        elif isinstance(self.extras.errors, list):
            self.extras.errors.append(error)
        else:
            self.extras.errors = [error]
        return False


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
