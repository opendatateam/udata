from mongoengine.errors import DoesNotExist

from udata.api_fields import get_fields
from udata.utils import filter_changed_fields, get_field_value_from_path

__all__ = ("Auditable",)


class Auditable(object):
    """Emit create/update/delete signals carrying the fields that actually changed.

    Lives here rather than next to the `Activity` document it feeds: recording an
    activity is only one of the things a domain model does with those signals, and
    every auditable model would otherwise have to import the activity package — which
    then could not reference those same models back.
    """

    def clean(self, **kwargs):
        super().clean()
        """
        Fetch original document changed fields values before the new one erase it.
        """
        changed_fields = self._get_changed_fields()
        if changed_fields:
            try:
                # `only` does not support having nested list as expressed in changed fields, ex resources.0.title
                # thus we only strip to direct attributes for simplicity
                direct_attributes = set(field.split(".")[0] for field in changed_fields)
                old_document = self.__class__.objects.only(*direct_attributes).get(pk=self.pk)
                self._previous_changed_fields = {}
                for field_path in changed_fields:
                    field_value = get_field_value_from_path(old_document, field_path)
                    self._previous_changed_fields[field_path] = field_value
            except DoesNotExist:
                pass

    @classmethod
    def post_save(cls, sender, document, **kwargs):
        try:
            auditable_fields = [
                key for key, field, info in get_fields(cls) if info.get("auditable", True)
            ]
        except Exception:
            # for backward compatibility, all fields are treated as auditable for classes not using field() function
            auditable_fields = document._get_changed_fields()
        changed_fields = [
            field
            for field in document._get_changed_fields()
            if field.split(".")[0] in auditable_fields
        ]
        if "post_save" in kwargs.get("ignores", []):
            return
        cls.after_save.send(document)
        if kwargs.get("created"):
            cls.on_create.send(document)
        elif len(changed_fields):
            previous = getattr(document, "_previous_changed_fields", {})
            # Filter changed_fields since mongoengine raises some false positive occurences
            changed_fields = filter_changed_fields(document, previous, changed_fields)
            if changed_fields:
                cls.on_update.send(document, changed_fields=changed_fields, previous=previous)
        if getattr(document, "deleted_at", None) or getattr(document, "deleted", None):
            cls.on_delete.send(document, **kwargs)
