import pytest
from mongoengine.connection import get_db

from udata.core.assistant.models import AssistantConversation
from udata.core.user.factories import UserFactory
from udata.db import migrations
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-11-27-delete-assistant-conversations-without-model.py"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


class DeleteAssistantConversationsWithoutModelMigrationTest(PytestOnlyDBTestCase):
    @pytest.mark.parametrize("stored", [{}, {"ai_model": None}], ids=["missing", "null"])
    def test_a_conversation_without_model_is_deleted(self, stored):
        # Inserted raw: the model now refuses a conversation without `ai_model`.
        AssistantConversation._get_collection().insert_one(
            {"chat_id": "chat-old", "user": UserFactory().id, "messages": [], **stored}
        )
        kept = AssistantConversation(user=UserFactory(), chat_id="chat-new", ai_model="first")
        kept.save()

        migrate()

        assert [c.id for c in AssistantConversation.objects] == [kept.id]

    def test_conversations_with_their_model_are_all_kept(self):
        user = UserFactory()
        for chat_id in ("chat-1", "chat-2"):
            AssistantConversation(user=user, chat_id=chat_id, ai_model="first").save()

        migrate()

        assert AssistantConversation.objects.count() == 2
