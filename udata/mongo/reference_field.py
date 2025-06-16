from mongoengine import DoesNotExist, ReferenceField


class SafeReferenceField(ReferenceField):
    def __get__(self, instance, owner):
        try:
            return super().__get__(instance, owner)
        except DoesNotExist:
            return None
