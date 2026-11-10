from mongoengine.fields import ListField, StringField

from udata import tags
from udata.i18n import lazy_gettext as _
from udata.tags import slug as slugify_tag


class TagListField(ListField):
    def __init__(self, **kwargs):
        self.tags = []
        super().__init__(StringField(), **kwargs)

    @staticmethod
    def from_input(input):
        if isinstance(input, list):
            return [tags.slug(value) for value in input]
        elif isinstance(input, str):
            return tags.tags_list(input)
        else:
            return []

    def clean(self, value):
        return sorted({slugify_tag(v) for v in value})

    def to_python(self, value):
        return super().to_python(self.clean(value))

    def to_mongo(self, value):
        return super().to_mongo(self.clean(value))

    def validate(self, values):
        super().validate(values)

        for tag in values:
            if not tags.TAG_MIN_LENGTH <= len(tag) <= tags.TAG_MAX_LENGTH:
                self.error(
                    _(
                        'Tag "%(tag)s" must be between %(min)d and %(max)d characters long.',
                        min=tags.TAG_MIN_LENGTH,
                        max=tags.TAG_MAX_LENGTH,
                        tag=tag,
                    )
                )
