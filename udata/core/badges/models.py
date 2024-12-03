import logging
from datetime import datetime

from mongoengine.signals import post_save

from udata.api_fields import field, generate_fields
from udata.auth import current_user
from udata.core.badges.fields import badge_fields
from udata.mongo import db

from .signals import on_badge_added, on_badge_removed

log = logging.getLogger(__name__)


__all__ = ["Badge", "BadgeMixin", "BadgesList"]

DEFAULT_BADGES_LIST_PARAMS = {
    "readonly": True,
    "inner_field_info": {"nested_fields": badge_fields},
}


@generate_fields(default_filterable_field="kind")
class Badge(db.EmbeddedDocument):
    meta = {"allow_inheritance": True}
    # The following field should be overloaded in descendants.
    kind = db.StringField(required=True)
    created = db.DateTimeField(default=datetime.utcnow, required=True)
    created_by = db.ReferenceField("User")

    def __str__(self):
        return self.kind


class BadgesList(db.EmbeddedDocumentListField):
    def __init__(self, badge_model, *args, **kwargs):
        return super(BadgesList, self).__init__(badge_model, *args, **kwargs)


class BadgeMixin:
    default_badges_list_params = DEFAULT_BADGES_LIST_PARAMS
    # The following field should be overloaded in descendants.
    badges = field(BadgesList(Badge), **DEFAULT_BADGES_LIST_PARAMS)

    def get_badge(self, kind):
        """Get a badge given its kind if present"""
        candidates = [b for b in self.badges if b.kind == kind]
        return candidates[0] if candidates else None

    def add_badge(self, kind):
        """Perform an atomic prepend for a new badge"""
        badge = self.get_badge(kind)
        if badge:
            return badge
        if kind not in getattr(self, "__badges__", {}):
            msg = "Unknown badge type for {model}: {kind}"
            raise db.ValidationError(msg.format(model=self.__class__.__name__, kind=kind))
        badge = self._fields["badges"].field.document_type(kind=kind)
        if current_user.is_authenticated:
            badge.created_by = current_user.id

        self.update(__raw__={"$push": {"badges": {"$each": [badge.to_mongo()], "$position": 0}}})
        self.reload()
        post_save.send(self.__class__, document=self)
        on_badge_added.send(self, kind=kind)
        return self.get_badge(kind)

    def remove_badge(self, kind):
        """Perform an atomic removal for a given badge"""
        self.update(__raw__={"$pull": {"badges": {"kind": kind}}})
        self.reload()
        on_badge_removed.send(self, kind=kind)
        post_save.send(self.__class__, document=self)

    def toggle_badge(self, kind):
        """Toggle a bdage given its kind"""
        badge = self.get_badge(kind)
        if badge:
            return self.remove_badge(kind)
        else:
            return self.add_badge(kind)

    def badge_label(self, badge):
        """Display the badge label for a given kind"""
        badge_model = self._fields["badges"].field.document_type
        kind = badge.kind if isinstance(badge, badge_model) else badge
        return self.__badges__[kind]
