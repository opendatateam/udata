import logging

from flask.signals import Namespace

log = logging.getLogger(__name__)

ns = Namespace()

#: Sent when a new HarvestSource is created
harvest_source_created = ns.signal('harvest:source-created')

#: Sent when a HarvestSource is updated
harvest_source_updated = ns.signal('harvest:source-updated')

#: Sent when a HarvestSource is deleted
harvest_source_deleted = ns.signal('harvest:source-deleted')

#: Run before each harvest job
before_harvest_job = ns.signal('harvest:before-job')

#: Run before each harvest job
after_harvest_job = ns.signal('harvest:after-job')

#: Sent when a new HarvestJob started
harvest_job_started = ns.signal('harvest:job-started')

#: Sent when a HarvestJob is done
harvest_job_done = ns.signal('harvest:job-done')

#: Sent when a HarvestJob failed
harvest_job_failed = ns.signal('harvest:job-failed')

#: Sent when a HarvestItem start
harvest_item_started = ns.signal('harvest:item-started')

#: Sent when a HarvestItem is done
harvest_item_done = ns.signal('harvest:item-done')

#: Sent when a HarvestItem failed
harvest_item_failed = ns.signal('harvest:item-failed')

#: Sent when a HarvestSource is scheduled
harvest_source_scheduled = ns.signal('harvest:source-scheduled')

#: Sent when a HarvestSource is unscheduled
harvest_source_unscheduled = ns.signal('harvest:source-unscheduled')
