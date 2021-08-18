import pytest

from udata.core.discussions.factories import (
    MessageDiscussionFactory, DiscussionFactory
)
from udata.core.followers.models import Follow
from udata.core.user.factories import UserFactory
from udata.core.user.models import User
from udata.core.organization.factories import OrganizationFactory

pytestmark = pytest.mark.usefixtures('clean_db')


@pytest.mark.frontend
class UserModelTest:
    modules = []  # Required for mails

    def test_mark_as_deleted(self):
        user = UserFactory()
        other_user = UserFactory()
        org = OrganizationFactory(editors=[user])
        discussion = DiscussionFactory(user=user, subject=org, discussion=[
            MessageDiscussionFactory(posted_by=user)
        ])
        user_follow_org = Follow.objects.create(follower=user, following=org)
        user_followed = Follow.objects.create(follower=other_user, following=user)

        user.mark_as_deleted()

        org.reload()
        assert len(org.members) == 0

        discussion.reload()
        assert discussion.discussion[0].content == 'DELETED'

        assert Follow.objects(id=user_follow_org.id).first() is None
        assert Follow.objects(id=user_followed.id).first() is None

        assert user.slug == 'deleted'

    def test_mark_as_deleted_slug_multiple(self):
        user = UserFactory()
        other_user = UserFactory()

        user.mark_as_deleted()
        other_user.mark_as_deleted()

        assert user.slug == 'deleted'
        assert other_user.slug == 'deleted-1'

    def test_delete_safeguard(self):
        user = UserFactory()
        with pytest.raises(NotImplementedError):
            user.delete()
        user._delete()
        assert User.objects.filter(id=user.id).count() == 0
