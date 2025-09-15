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

    def validate(self, **kwargs):
        """
        Make sure that either title or element is set.
        (Empty nested element is a valid use case for "placeholder" elements)
        """
        validation = super().validate(**kwargs)
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

    @property
    def data(self):
        """Override to exclude non-model fields from data"""
        # Get the base data from WTForms
        base_data = super().data
        # Filter out non-model fields
        return {name: value for name, value in base_data.items() if name != "elements"}

    def populate_obj(self, obj):
        """Override populate_obj to exclude non-model fields"""
        # Only populate model fields, skip elements
        for name, field in self._fields.items():
            if name != "elements":
                field.populate_obj(obj, name)

    def save(self, commit=True, **kwargs):
        """Custom save to handle TopicElement creation properly"""
        # Store elements data before parent save
        elements_data = self.elements.data
        # Check if elements field was explicitly provided
        elements_provided = self.elements.has_data

        # Use parent save method (elements field is excluded via populate_obj)
        topic = super().save(commit=commit, **kwargs)

        # Only clear and recreate elements if they were explicitly provided in the payload
        if elements_provided:
            if commit:
                TopicElement.objects(topic=topic).delete()

            # Create elements and associate them with the topic
            for element_data in elements_data or []:
                # Create element form with only its own data, not inheriting from parent
                element_form = TopicElementForm(meta={"csrf": False})
                element_form.process(data=element_data)
                if element_form.validate():
                    element = element_form.save(commit=False)
                    element.topic = topic
                    if commit:
                        element.save()

        return topic

    spatial = SpatialCoverageField(
        _("Spatial coverage"), description=_("The geographical area covered by the data.")
    )

    tags = fields.TagField(_("Tags"), [validators.DataRequired()])
    private = fields.BooleanField(_("Private"))
    featured = fields.BooleanField(_("Featured"))
    extras = fields.ExtrasField()
