import factory

from udata.core.api_token.hashing import hash_token
from udata.core.user.factories import UserFactory
from udata.factories import ModelFactory

from .oauth2 import OAuth2Client, OAuth2Token

CLIENT_SECRET = "suchs3cr3t"


class OAuth2ClientFactory(ModelFactory):
    class Meta:
        model = OAuth2Client

    name = factory.Faker("company")
    owner = factory.SubFactory(UserFactory)
    redirect_uris = factory.LazyFunction(lambda: ["https://app.example.org/callback"])
    # Stored hashed, as `create_oauth_client` does: the client authenticates with `CLIENT_SECRET`.
    secret = factory.LazyFunction(lambda: hash_token(CLIENT_SECRET))


class OAuth2TokenFactory(ModelFactory):
    class Meta:
        model = OAuth2Token

    class Params:
        # What the application holds. Only their hashes are stored, as `save_token` does.
        access = factory.Faker("uuid4")
        refresh = factory.Faker("uuid4")

    client = factory.SubFactory(OAuth2ClientFactory)
    user = factory.SubFactory(UserFactory)
    access_token = factory.LazyAttribute(lambda token: hash_token(token.access))
    refresh_token = factory.LazyAttribute(lambda token: hash_token(token.refresh))
