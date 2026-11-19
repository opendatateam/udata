from mongoengine.connection import get_db

from udata.core.api_token.models import ApiToken
from udata.core.user.factories import AdminFactory, UserFactory
from udata.db import migrations
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-11-19-rename-api-token-admin-scope.py"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


def legacy_token(user):
    """A token as stored before the migration: the `admin` scope is no longer a valid
    choice, so it is written past the model."""
    token, _plaintext = ApiToken.generate(user)
    ApiToken._get_collection().update_one({"_id": token.id}, {"$set": {"scopes": ["admin"]}})
    return token


class RenameApiTokenAdminScopeMigrationTest(PytestOnlyDBTestCase):
    def test_a_sysadmin_token_keeps_its_rights_as_sysadmin(self):
        token = legacy_token(AdminFactory())

        migrate()

        assert ApiToken.objects.get(id=token.id).scopes == ["sysadmin"]

    def test_another_user_token_loses_the_scope(self):
        sysadmin_token = legacy_token(AdminFactory())
        user_token = legacy_token(UserFactory())

        migrate()

        assert ApiToken.objects.get(id=sysadmin_token.id).scopes == ["sysadmin"]
        assert ApiToken.objects.get(id=user_token.id).scopes == []

    def test_without_any_sysadmin_every_token_loses_the_scope(self):
        token = legacy_token(UserFactory())

        migrate()

        assert ApiToken.objects.get(id=token.id).scopes == []

    def test_a_token_without_scope_is_left_alone(self):
        token, _plaintext = ApiToken.generate(AdminFactory())

        migrate()

        assert ApiToken.objects.get(id=token.id).scopes == []
