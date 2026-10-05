from udata.core.dataset.models import Dataset
from udata.features.notifications.constants import NotificationCategory, NotificationReason
from udata.features.notifications.events import NotificationEvent, Recipient


class DatasetReusedEvent(NotificationEvent):
    """Somebody plugged something of theirs onto a dataset of ours.

    Reuses and dataservices differ only by the object they carry: the same people hear
    about it, on the same grounds, scoped to the same dataset — so the answer lives
    here once rather than twice.
    """

    category = NotificationCategory.REUSES
    dataset: Dataset

    def recipients(self):
        recipients = []
        if self.dataset.owner:
            recipients.append(Recipient(self.dataset.owner, frozenset({NotificationReason.OWNER})))
        if self.dataset.organization:
            # Editors are left out: being told that somebody reused a dataset is
            # something you act on as the publisher, not as a contributor.
            recipients += [
                Recipient.from_member(member)
                for member in self.dataset.organization.by_role("admin")
            ]
        return recipients

    def scopes(self):
        scopes = [self.dataset]
        if self.dataset.organization:
            scopes.append(self.dataset.organization)
        return scopes


def became_public(document, changed_fields, previous) -> bool:
    """Whether this update is the one publishing a reuse or a dataservice, which is when
    it gets announced if it was created private."""
    return "private" in changed_fields and bool(previous.get("private")) and not document.private
