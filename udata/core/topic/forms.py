from udata.core.spatial.forms import SpatialCoverageField
from udata.forms import ModelForm, fields, validators
from udata.i18n import lazy_gettext as _

from .models import Topic

__all__ = ("TopicForm",)


class TopicForm(ModelForm):
    model_class = Topic

    owner = fields.CurrentUserField()
    organization = fields.PublishAsField(_("Publish as"))

    name = fields.StringField(_("Name"), [validators.DataRequired()])
    description = fields.MarkdownField(_("Description"), [validators.DataRequired()])

    datasets = fields.DatasetListField(_("Associated datasets"))
    reuses = fields.ReuseListField(_("Associated reuses"))

    spatial = SpatialCoverageField(
        _("Spatial coverage"), description=_("The geographical area covered by the data.")
    )

    tags = fields.TagField(_("Tags"), [validators.DataRequired()])
    private = fields.BooleanField(_("Private"))
    featured = fields.BooleanField(_("Featured"))
    extras = fields.ExtrasField()
