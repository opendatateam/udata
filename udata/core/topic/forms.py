from udata.core.spatial.forms import SpatialCoverageField
from udata.forms import ModelForm, fields, validators
from udata.i18n import lazy_gettext as _

from .models import Topic, TopicElement

__all__ = ("TopicForm", "TopicElementForm")


class TopicElementForm(ModelForm):
    model_class = TopicElement

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

    def save(self, commit=True, **kwargs):
        """Custom save to handle TopicElement creation properly"""
        # Handle elements manually before saving the topic
        saved_elements = []
        if self.elements.data:
            for element_data in self.elements.data:
                # Create and populate TopicElement instance
                element_form = TopicElementForm(data=element_data)
                if element_form.validate():
                    element = element_form.save()  # This will save the TopicElement
                    saved_elements.append(element)

        # Save the topic with the default behavior but without committing
        topic = super().save(commit=False, **kwargs)

        # Replace elements with our saved ones
        topic.elements = saved_elements

        if commit:
            topic.save()

        return topic

    spatial = SpatialCoverageField(
        _("Spatial coverage"), description=_("The geographical area covered by the data.")
    )

    tags = fields.TagField(_("Tags"), [validators.DataRequired()])
    private = fields.BooleanField(_("Private"))
    featured = fields.BooleanField(_("Featured"))
    extras = fields.ExtrasField()
