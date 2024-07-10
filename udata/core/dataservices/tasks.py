from celery.utils.log import get_task_logger

from udata.core.dataservices.models import Dataservice

# from udata.harvest.models import HarvestJob
from udata.models import Discussion, Follow, Transfer
from udata.tasks import job

log = get_task_logger(__name__)


@job("purge-dataservices")
def purge_dataservices(self):
    for dataservice in Dataservice.objects(deleted_at__ne=None):
        log.info(f"Purging dataservice {dataservice}")
        # Remove followers
        Follow.objects(following=dataservice).delete()
        # Remove discussions
        Discussion.objects(subject=dataservice).delete()
        # Remove HarvestItem references
        # TODO: uncomment when adding dataservice harvest
        # HarvestJob.objects(items__dataservice=dataservice).update(set__items__S__dataservice=None)
        # Remove associated Transfers
        Transfer.objects(subject=dataservice).delete()
        # Remove dataservice
        dataservice.delete()
