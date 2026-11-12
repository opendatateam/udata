from udata.core.dataset.models import Dataset
from udata.features.notifications.events import NotificationEvent, responsible_recipients


class DatasetReusedEvent(NotificationEvent):
    """Somebody plugged something of theirs onto a dataset of ours.

    Reuses and dataservices differ only by the object they carry: the same people hear
    about it, on the same grounds, scoped to the same dataset — so the answer lives
    here once rather than twice.
    """

    dataset: Dataset

    @property
    def subject(self):
        return self.dataset

    def recipients(self):
        return responsible_recipients(self.dataset)


def became_public(document, changed_fields, previous) -> bool:
    """Whether this update publishes a reuse or a dataservice, which is when it gets
    announced if it was created private. Publishing it again after hiding it announces
    nothing new: the events skip whoever already heard about it."""
    return "private" in changed_fields and bool(previous.get("private")) and not document.private
