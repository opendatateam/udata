from udata import mail
from udata.i18n import lazy_gettext as _
from udata.core import storages
from udata.models import Activity, Issue, Discussion, Follow
from udata.tasks import get_logger, job, task

from .models import Reuse

log = get_logger(__name__)


@job('purge-reuses')
def purge_reuses(self):
    for reuse in Reuse.objects(deleted__ne=None):
        log.info(f'Purging reuse {reuse}')
        # Remove followers
        Follow.objects(following=reuse).delete()
        # Remove issues
        Issue.objects(subject=reuse).delete()
        # Remove discussions
        Discussion.objects(subject=reuse).delete()
        # Remove activity
        Activity.objects(related_to=reuse).delete()
        # Remove reuse's logo in all sizes
        if reuse.image.filename is not None:
            storage = storages.images
            storage.delete(reuse.image.filename)
            storage.delete(reuse.image.original)
            for key, value in reuse.image.thumbnails.items():
                storage.delete(value)
        reuse.delete()


@task
def notify_new_reuse(reuse_id):
    reuse = Reuse.objects.get(pk=reuse_id)
    for dataset in reuse.datasets:
        if dataset.organization:
            recipients = [m.user for m in dataset.organization.members]
        elif dataset.owner:
            recipients = dataset.owner
        else:
            recipients = None
        if recipients:
            mail.send(_('New reuse'), recipients, 'new_reuse', reuse=reuse,
                      dataset=dataset)
