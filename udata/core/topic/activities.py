from flask_security import current_user

from udata.i18n import lazy_gettext as _
from udata.models import Activity, Topic, db

__all__ = ("UserCreatedTopic", "UserUpdatedTopic", "TopicRelatedActivity")


class TopicRelatedActivity(object):
    related_to = db.ReferenceField("Topic")


class UserCreatedTopic(TopicRelatedActivity, Activity):
    key = "topic:created"
    icon = "fa fa-plus"
    badge_type = "success"
    label = _("created a topic")


class UserUpdatedTopic(TopicRelatedActivity, Activity):
    key = "topic:updated"
    icon = "fa fa-pencil"
    label = _("updated a topic")


@Topic.on_create.connect
def on_user_created_topic(topic):
    if current_user and current_user.is_authenticated:
        UserCreatedTopic.emit(topic, topic.organization)


@Topic.on_update.connect
def on_user_updated_topic(topic, **kwargs):
    changed_fields = kwargs.get("changed_fields", [])
    if current_user and current_user.is_authenticated:
        UserUpdatedTopic.emit(topic, topic.organization, changed_fields)
