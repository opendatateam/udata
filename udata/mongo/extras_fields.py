import logging
from datetime import date, datetime

from mongoengine import EmbeddedDocument
from mongoengine.fields import BaseField, DictField

log = logging.getLogger(__name__)


ALLOWED_TYPES = (str, int, float, bool, datetime, date, list, dict)


class ExtrasField(DictField):
    def __init__(self, **kwargs):
        self.registered = {}
        super(ExtrasField, self).__init__()

    def register(self, key, dbtype):
        """Register a DB type to add constraint on a given extra key"""
        if not issubclass(dbtype, (BaseField, EmbeddedDocument)):
            msg = "ExtrasField can only register MongoEngine fields"
            raise TypeError(msg)
        self.registered[key] = dbtype

    def validate(self, values):
        super(ExtrasField, self).validate(values)

        errors = {}
        for key, value in values.items():
            extra_cls = self.registered.get(key)

            if not extra_cls:
                if not isinstance(value, ALLOWED_TYPES):
                    types = ", ".join(t.__name__ for t in ALLOWED_TYPES)
                    msg = "Value should be an instance of: {types}"
                    errors[key] = msg.format(types=types)
                continue

            try:
                if issubclass(extra_cls, EmbeddedDocument):
                    (
                        value.validate()
                        if isinstance(value, extra_cls)
                        else extra_cls(**value).validate()
                    )
                else:
                    extra_cls().validate(value)
            except Exception as e:
                errors[key] = getattr(e, "message", str(e))

        if errors:
            self.error("Unsupported types", errors=errors)

    def __call__(self, key):
        def inner(cls):
            self.register(key, cls)
            return cls

        return inner

    def to_python(self, value):
        if isinstance(value, EmbeddedDocument):
            return value
        return super(ExtrasField, self).to_python(value)


class OrganizationExtrasField(ExtrasField):
    def __init__(self, **kwargs):
        super(OrganizationExtrasField, self).__init__()

    def validate(self, values):
        super(ExtrasField, self).validate(values)

        errors = {}

        mandatory_keys = ["title", "description", "type"]
        optional_keys = ["choices"]
        valid_types = ["str", "int", "float", "bool", "datetime", "date", "choice"]

        for elem in values.get("custom", []):
            # Check if all mandatory keys are in the dictionary
            if not all(key in elem for key in mandatory_keys):
                errors["custom"] = (
                    "The dictionary does not contain the mandatory keys: 'title', 'description', 'type'."
                )

            # Check if the dictionary contains only keys that are either mandatory or optional
            if not all(key in mandatory_keys + optional_keys for key in elem):
                errors["custom"] = "The dictionary does contains extra keys than allowed ones."

            # Check if the "type" value is one of the valid types
            if elem.get("type") not in valid_types:
                errors["type"] = "Type '{type}' of '{title}' should be one of: {types}".format(
                    type=elem.get("type"), title=elem.get("title"), types=valid_types
                )

            # Check if the "choices" key is present only if the type is "choice" and it's not an empty list
            is_choices_valid = True
            if elem.get("type") == "choice":
                is_choices_valid = (
                    "choices" in elem
                    and isinstance(elem["choices"], list)
                    and len(elem["choices"]) > 0
                )
            elif "choices" in elem:
                is_choices_valid = False
            if not is_choices_valid:
                errors["choices"] = (
                    "The 'choices' key must be an non empty list and can only be present when type 'choice' is selected."
                )

        if errors:
            self.error("Custom extras error", errors=errors)
