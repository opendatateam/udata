from udata.forms import ModelForm, fields, validators
from udata.i18n import lazy_gettext as _
from udata.models import User

from .models import AVATAR_SIZES


__all__ = ('UserProfileForm', 'UserProfileAdminForm')


class UserProfileForm(ModelForm):
    model_class = User

    first_name = fields.StringField(_('First name'), [validators.DataRequired()])
    last_name = fields.StringField(_('Last name'), [validators.DataRequired()])
    avatar = fields.ImageField(_('Avatar'), sizes=AVATAR_SIZES)
    website = fields.URLField(_('Website'))
    about = fields.MarkdownField(_('About'))


class UserProfileAdminForm(UserProfileForm):
    roles = fields.RolesField(_('Roles'))
    active = fields.BooleanField()
