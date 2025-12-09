from udata.core import storages
from udata.core.pages.models import Page
from udata.core.topic.models import TopicElement
from udata.models import Activity, Discussion, Follow, Transfer
from udata.tasks import get_logger, job, task

from . import mails
from .models import Reuse

log = get_logger(__name__)


@job("purge-reuses")
def purge_reuses(self) -> None:
    for reuse in Reuse.objects(deleted__ne=None):
        log.info(f"Purging reuse {reuse}")
        # Remove followers
        Follow.objects(following=reuse).delete()
        # Remove discussions
        Discussion.objects(subject=reuse).delete()
        # Remove activity
        Activity.objects(related_to=reuse).delete()
        # Remove transfers
        Transfer.objects(subject=reuse).delete()
        # Remove reuses references in Topics
        TopicElement.objects(element=reuse).update(element=None)
        # Remove reuses in pages (mongoengine doesn't support updating a field in a generic embed)
        Page._get_collection().update_many(
            {"blocs.reuses": reuse.id},
            {"$pull": {"blocs.$[b].reuses": reuse.id}},
            array_filters=[{"b.reuses": reuse.id}],
        )
        # Remove reuse's logo in all sizes
        if reuse.image.filename is not None:
            storage = storages.images
            storage.delete(reuse.image.filename)
            storage.delete(reuse.image.original)
            for key, value in reuse.image.thumbnails.items():
                storage.delete(value)
        reuse.delete()


@task
def notify_new_reuse(reuse_id: int) -> None:
    reuse = Reuse.objects.get(pk=reuse_id)
    for dataset in reuse.datasets:
        if dataset.organization:
            recipients = [m.user for m in dataset.organization.members]
        elif dataset.owner:
            recipients = dataset.owner
        else:
            recipients = None
        if recipients:
            mails.new_reuse(reuse, dataset).send(recipients)
