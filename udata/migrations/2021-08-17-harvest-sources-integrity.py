'''
Remove PeriodicTask attached to deleted HarvestSource
'''
import logging

from udata.core.jobs.models import PeriodicTask
from udata.harvest.models import HarvestSource

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing PeriodicTask objects.')

    harvest_schedules = PeriodicTask.objects.filter(name__startswith='Harvest',
                                                    description='Periodic Harvesting')
    hs = HarvestSource.objects.filter(periodic_task__in=harvest_schedules)
    unlegit_schedules = harvest_schedules.filter(id__nin=[h.periodic_task.id for h in hs])
    count = unlegit_schedules.delete()

    log.info(f'Completed, removed {count} PeriodicTask objects')
