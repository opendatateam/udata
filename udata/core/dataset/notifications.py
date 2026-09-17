from udata.core.dataset.models import Dataset
from udata.features.notifications.constants import NotificationReason
from udata.features.notifications.events import NotificationEvent, Recipient, merge_recipients


class DatasetReusedEvent(NotificationEvent):
    """Somebody plugged something of theirs onto a dataset of ours.

    Reuses and dataservices differ only by the object they carry: the same people hear
    about it, on the same grounds, scoped to the same dataset — so the answer lives
    here once rather than twice.
    """

    dataset: Dataset

    def recipients(self):
        recipients = []
        if self.dataset.owner:
            recipients.append(Recipient(self.dataset.owner, frozenset({NotificationReason.OWNER})))
        if self.dataset.organization:
            # Editors are left out: being told that somebody reused a dataset is
            # something you act on as the publisher, not as a contributor.
            recipients += [
                Recipient(member.user, frozenset({NotificationReason.ORGANIZATION_ADMIN}))
                for member in self.dataset.organization.by_role("admin")
            ]
        return merge_recipients(recipients)

    def scopes(self):
        scopes = [self.dataset]
        if self.dataset.organization:
            scopes.append(self.dataset.organization)
        return scopes
