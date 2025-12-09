from celery.utils.log import get_task_logger
from flask import current_app

from udata.core.badges import tasks as badge_tasks
from udata.core.constants import HVD
from udata.core.dataservices.models import Dataservice
from udata.core.organization.constants import CERTIFIED, PUBLIC_SERVICE
from udata.core.organization.models import Organization
from udata.core.pages.models import Page
from udata.core.topic.models import TopicElement
from udata.harvest.models import HarvestJob
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
        HarvestJob.objects(items__dataservice=dataservice).update(set__items__S__dataservice=None)
        # Remove associated Transfers
        Transfer.objects(subject=dataservice).delete()
        # Remove dataservices references in Topics
        TopicElement.objects(element=dataservice).update(element=None)
        # Remove dataservices in pages (mongoengine doesn't support updating a field in a generic embed)
        Page._get_collection().update_many(
            {"blocs.dataservices": dataservice.id},
            {"$pull": {"blocs.$[b].dataservices": dataservice.id}},
            array_filters=[{"b.dataservices": dataservice.id}],
        )
        # Remove dataservice
        dataservice.delete()


@badge_tasks.register(model=Dataservice, badge=HVD)
def update_dataservice_hvd_badge() -> None:
    """
    Update HVD badges to candidate dataservices, based on the hvd tag.
    Only dataservices owned by certified and public service organizations are candidate to have a HVD badge.
    """
    if not current_app.config["HVD_SUPPORT"]:
        log.error("You need to set HVD_SUPPORT if you want to update dataservice hvd badge")
        return
    public_certified_orgs = (
        Organization.objects(badges__kind=PUBLIC_SERVICE).filter(badges__kind=CERTIFIED).only("id")
    )

    dataservices = Dataservice.objects(
        tags="hvd", badges__kind__ne="hvd", organization__in=public_certified_orgs
    )
    log.info(f"Adding HVD badge to {dataservices.count()} dataservices")
    for dataservice in dataservices:
        dataservice.add_badge(HVD)

    dataservices = Dataservice.objects(
        tags__nin=["hvd"], badges__kind="hvd", organization__in=public_certified_orgs
    )
    log.info(f"Remove HVD badge from {dataservices.count()} dataservices")
    for dataservice in dataservices:
        dataservice.remove_badge(HVD)
