from mongoengine.fields import ListField, StringField
from slugify import slugify

from udata import tags
from udata.i18n import lazy_gettext as _


class TagListField(ListField):
    def __init__(self, **kwargs):
        self.tags = []
        super(TagListField, self).__init__(StringField(), **kwargs)

    @staticmethod
    def from_input(input):
        if isinstance(input, list):
            return [tags.slug(value) for value in input]
        elif isinstance(input, str):
            return tags.tags_list(input)
        else:
            return []

    def clean(self, value):
        return sorted(list(set([slugify(v, to_lower=True) for v in value])))

    def to_python(self, value):
        return super(TagListField, self).to_python(self.clean(value))

    def to_mongo(self, value):
        return super(TagListField, self).to_mongo(self.clean(value))

    def validate(self, values):
        super(TagListField, self).validate(values)

        for tag in values:
            if not tags.MIN_TAG_LENGTH <= len(tag) <= tags.MAX_TAG_LENGTH:
                self.error(
                    _(
                        'Tag "%(tag)s" must be between %(min)d and %(max)d characters long.',
                        min=tags.MIN_TAG_LENGTH,
                        max=tags.MAX_TAG_LENGTH,
                        tag=tag,
                    )
                )
