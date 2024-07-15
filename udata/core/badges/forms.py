from udata.forms import ModelForm, fields, validators
from udata.i18n import lazy_gettext as _
from udata.models import Badge

__all__ = ("badge_form",)


def badge_form(model):
    """A form factory for a given model badges"""

    class BadgeForm(ModelForm):
        model_class = Badge

        kind = fields.RadioField(
            _("Kind"),
            [validators.DataRequired()],
            choices=list(model.__badges__.items()),
            description=_("Kind of badge (certified, etc)"),
        )

    return BadgeForm
