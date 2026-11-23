from gettext import gettext as _

from mongoengine.queryset import DoesNotExist
from wtforms import widgets
from wtforms.fields import SelectFieldBase
from wtforms.validators import ValidationError


class QuerySetSelectField(SelectFieldBase):
    """
    Resolve the submitted ID against a QuerySet: the `data` property stores
    the model instance, not the ID. Submitting an ID which is not in the
    queryset will result in a validation error.

    If `allow_blank` is set to `True`, submitting `__None` sets `data` to `None`.
    """

    widget = widgets.Select()

    def __init__(
        self,
        label="",
        validators=None,
        queryset=None,
        allow_blank=False,
        **kwargs,
    ):
        super().__init__(label, validators, **kwargs)
        self.allow_blank = allow_blank
        self.queryset = queryset

    def process_formdata(self, valuelist):
        if valuelist:
            if valuelist[0] == "__None":
                self.data = None
            else:
                if self.queryset is None:
                    self.data = None
                    return

                try:
                    obj = self.queryset.get(pk=valuelist[0])
                    self.data = obj
                except DoesNotExist:
                    self.data = None

    def pre_validate(self, form):
        if (not self.allow_blank or self.data is not None) and not self.data:
            raise ValidationError(_("Not a valid choice"))


class ModelSelectField(QuerySetSelectField):
    """
    Like a QuerySetSelectField, except takes a model class instead of a
    queryset and lists everything in it.
    """

    def __init__(self, label="", validators=None, model=None, **kwargs):
        queryset = kwargs.pop("queryset", model.objects)
        super().__init__(label, validators, queryset=queryset, **kwargs)
