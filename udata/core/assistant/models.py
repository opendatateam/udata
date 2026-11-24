from mongoengine import EmbeddedDocument
from mongoengine.fields import (
    EmbeddedDocumentField,
    ListField,
    ReferenceField,
    StringField,
)
from pydantic import ConfigDict, TypeAdapter
from pydantic_ai.messages import ModelMessage

from udata.mongo.datetime_fields import Datetimed
from udata.mongo.document import UDataDocument as Document

__all__ = ("AssistantConversation", "AssistantMessage")

# One message, with the settings of pydantic-ai's ModelMessagesTypeAdapter.
MESSAGE_ADAPTER = TypeAdapter(
    ModelMessage,
    config=ConfigDict(defer_build=True, ser_json_bytes="base64", val_json_bytes="base64"),
)


class AssistantMessage(EmbeddedDocument):
    # JSON text, not a dict: Mongo refuses keys with a dot, as column names may have.
    content = StringField(required=True)


class AssistantConversation(Datetimed, Document):
    """A conversation with the assistant, as the model reads it again on the next turn."""

    # The chat id the client sends: unique per user only.
    chat_id = StringField(required=True)
    user = ReferenceField("User", required=True)
    subject = ReferenceField("Dataset")
    messages = ListField(EmbeddedDocumentField(AssistantMessage))

    meta = {
        "indexes": [{"fields": ["user", "chat_id"], "unique": True}],
        "auto_create_index_on_save": True,
    }

    def model_messages(self) -> list[ModelMessage]:
        return [MESSAGE_ADAPTER.validate_json(stored.content) for stored in self.messages]

    @staticmethod
    def stored_messages(messages: list[ModelMessage]) -> list[AssistantMessage]:
        return [
            AssistantMessage(content=MESSAGE_ADAPTER.dump_json(message).decode())
            for message in messages
        ]
