import factory

from udata.core.user.factories import UserFactory
from udata.factories import ModelFactory

from .oauth2 import OAuth2Client, OAuth2Token


class OAuth2ClientFactory(ModelFactory):
    class Meta:
        model = OAuth2Client

    name = factory.Faker("company")
    owner = factory.SubFactory(UserFactory)
    redirect_uris = factory.LazyFunction(lambda: ["https://app.example.org/callback"])
    secret = factory.Faker("password")


class OAuth2TokenFactory(ModelFactory):
    class Meta:
        model = OAuth2Token

    client = factory.SubFactory(OAuth2ClientFactory)
    user = factory.SubFactory(UserFactory)
    access_token = factory.Faker("uuid4")
    refresh_token = factory.Faker("uuid4")
    expires_in = 30 * 24 * 60 * 60
