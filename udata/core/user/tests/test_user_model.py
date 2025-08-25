import pytest

from udata.core.discussions.factories import DiscussionFactory, MessageDiscussionFactory
from udata.core.discussions.models import Discussion
from udata.core.followers.models import Follow
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.core.user.models import User

pytestmark = pytest.mark.usefixtures("clean_db")


@pytest.mark.frontend
class UserModelTest:
    modules = []  # Required for mails

    def test_mark_as_deleted(self):
        user = UserFactory()
        other_user = UserFactory()
        org = OrganizationFactory(editors=[user])
        discussion = DiscussionFactory(
            user=user,
            subject=org,
            discussion=[
                MessageDiscussionFactory(posted_by=user),
                MessageDiscussionFactory(posted_by=user),
            ],
        )
        user_follow_org = Follow.objects.create(follower=user, following=org)
        user_followed = Follow.objects.create(follower=other_user, following=user)

        user.mark_as_deleted()

        org.reload()
        assert len(org.members) == 0

        # discussions are kept by default
        discussion.reload()
        assert len(discussion.discussion) == 2
        assert discussion.discussion[1].content != "DELETED"

        assert Follow.objects(id=user_follow_org.id).first() is None
        assert Follow.objects(id=user_followed.id).first() is None

        assert user.slug == f"deleted-{user.id}"

    def test_mark_as_deleted_with_comments_deletion(self):
        user = UserFactory()
        other_user = UserFactory()
        discussion_only_user = DiscussionFactory(
            user=user,
            discussion=[
                MessageDiscussionFactory(posted_by=user),
                MessageDiscussionFactory(posted_by=user),
            ],
        )
        discussion_with_other = DiscussionFactory(
            user=other_user,
            discussion=[
                MessageDiscussionFactory(posted_by=other_user),
                MessageDiscussionFactory(posted_by=user),
            ],
        )

        user.mark_as_deleted(delete_comments=True)

        assert Discussion.objects(id=discussion_only_user.id).first() is None
        discussion_with_other.reload()
        assert discussion_with_other.discussion[1].content == "DELETED"

    def test_mark_as_deleted_slug_multiple(self):
        user = UserFactory()
        other_user = UserFactory()

        user.mark_as_deleted()
        other_user.mark_as_deleted()

        assert user.slug == f"deleted-{user.id}"
        assert other_user.slug == f"deleted-{other_user.id}"

    def test_delete_safeguard(self):
        user = UserFactory()
        with pytest.raises(NotImplementedError):
            user.delete()
        user._delete()
        assert User.objects.filter(id=user.id).count() == 0
