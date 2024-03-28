from slugify import slugify

from mongoengine.fields import ListField, StringField


class TagListField(ListField):
    def __init__(self, **kwargs):
        self.tags = []
        super(TagListField, self).__init__(StringField(), **kwargs)

    def clean(self, value):
        return sorted(list(set([slugify(v, to_lower=True) for v in value])))

    def to_python(self, value):
        return super(TagListField, self).to_python(self.clean(value))

    def to_mongo(self, value):
        return super(TagListField, self).to_mongo(self.clean(value))
