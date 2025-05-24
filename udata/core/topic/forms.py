from udata.core.spatial.forms import SpatialCoverageField
from udata.forms import ModelForm, fields, validators
from udata.i18n import lazy_gettext as _

from .models import Topic, TopicElement

__all__ = ("TopicForm", "TopicElementForm")


class TopicElementForm(ModelForm):
    model_class = TopicElement

    # FIXME: add this?
    # id = fields.UUIDField()

    title = fields.StringField(_("Title"))
    description = fields.StringField(_("Description"))
    tags = fields.TagField(_("Tags"))
    extras = fields.ExtrasField()
    element = fields.ModelField(_("Element"))

    def validate(self, extra_validators=None):
        validation = super().validate(extra_validators)
        if not self.element.data and not self.title.data:
            self.element.errors.append(_("A topic element must have a title or an element."))
            return False
        return validation


class TopicForm(ModelForm):
    model_class = Topic

    owner = fields.CurrentUserField()
    organization = fields.PublishAsField(_("Publish as"))

    name = fields.StringField(_("Name"), [validators.DataRequired()])
    description = fields.MarkdownField(_("Description"), [validators.DataRequired()])

    elements = fields.NestedModelList(TopicElementForm)

    spatial = SpatialCoverageField(
        _("Spatial coverage"), description=_("The geographical area covered by the data.")
    )

    tags = fields.TagField(_("Tags"), [validators.DataRequired()])
    private = fields.BooleanField(_("Private"))
    featured = fields.BooleanField(_("Featured"))
    extras = fields.ExtrasField()
