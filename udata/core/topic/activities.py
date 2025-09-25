from flask_security import current_user

from udata.core.topic.models import TopicElement
from udata.i18n import lazy_gettext as _
from udata.models import Activity, Topic, db

__all__ = (
    "UserCreatedTopic",
    "UserUpdatedTopic",
    "UserCreatedTopicElement",
    "UserUpdatedTopicElement",
    "UserDeletedTopicElement",
    "TopicRelatedActivity",
)


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


class UserCreatedTopicElement(TopicRelatedActivity, Activity):
    key = "topic:element:created"
    icon = "fa fa-plus"
    badge_type = "success"
    label = _("added an element to a topic")


class UserUpdatedTopicElement(TopicRelatedActivity, Activity):
    key = "topic:element:updated"
    icon = "fa fa-pencil"
    label = _("updated an element in a topic")


class UserDeletedTopicElement(TopicRelatedActivity, Activity):
    key = "topic:element:deleted"
    icon = "fa fa-remove"
    badge_type = "error"
    label = _("removed an element from a topic")


@Topic.on_create.connect
def on_user_created_topic(topic):
    if current_user and current_user.is_authenticated:
        UserCreatedTopic.emit(topic, topic.organization)


@Topic.on_update.connect
def on_user_updated_topic(topic, **kwargs):
    changed_fields = kwargs.get("changed_fields", [])
    if current_user and current_user.is_authenticated:
        UserUpdatedTopic.emit(topic, topic.organization, changed_fields)


@TopicElement.on_create.connect
def on_user_created_topic_element(topic_element):
    if current_user and current_user.is_authenticated and topic_element.topic:
        extras = {"element_id": str(topic_element.id)}
        UserCreatedTopicElement.emit(
            topic_element.topic, topic_element.topic.organization, extras=extras
        )


@TopicElement.on_update.connect
def on_user_updated_topic_element(topic_element, **kwargs):
    changed_fields = kwargs.get("changed_fields", [])
    if current_user and current_user.is_authenticated and topic_element.topic:
        extras = {"element_id": str(topic_element.id)}
        UserUpdatedTopicElement.emit(
            topic_element.topic, topic_element.topic.organization, changed_fields, extras=extras
        )


@TopicElement.on_delete.connect
def on_user_deleted_topic_element(topic_element):
    if current_user and current_user.is_authenticated and topic_element.topic:
        extras = {"element_id": str(topic_element.id)}
        UserDeletedTopicElement.emit(
            topic_element.topic, topic_element.topic.organization, extras=extras
        )
