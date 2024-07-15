from udata.forms import ModelForm, fields, validators, widgets
from udata.i18n import lazy_gettext as _

from .constants import IMAGE_SIZES
from .models import Post

__all__ = ("PostForm",)


class PostForm(ModelForm):
    model_class = Post

    owner = fields.CurrentUserField()

    name = fields.StringField(_("Name"), [validators.DataRequired()])
    headline = fields.StringField(_("Headline"), widget=widgets.TextArea())
    content = fields.MarkdownField(_("Content"), [validators.DataRequired()])

    datasets = fields.DatasetListField(_("Associated datasets"))
    reuses = fields.ReuseListField(_("Associated reuses"))

    image = fields.ImageField(_("Image"), sizes=IMAGE_SIZES)
    credit_to = fields.StringField(_("Image credits"))
    credit_url = fields.URLField(_("Credit URL"))

    tags = fields.TagField(_("Tags"))

    body_type = fields.StringField(
        _("body type"), description=_("Specify your body type (HTML or markdown)")
    )
