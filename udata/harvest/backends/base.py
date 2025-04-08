import logging
import traceback
from datetime import date, datetime, timedelta
from uuid import UUID

import requests
from flask import current_app
from voluptuous import MultipleInvalid, RequiredFieldInvalid

import udata.uris as uris
from udata.core.dataservices.models import Dataservice
from udata.core.dataservices.models import HarvestMetadata as HarvestDataserviceMetadata
from udata.core.dataset.models import HarvestDatasetMetadata
from udata.models import Dataset
from udata.utils import safe_unicode

from ..exceptions import HarvestException, HarvestSkipException, HarvestValidationError
from ..models import (
    HarvestError,
    HarvestItem,
    HarvestJob,
    HarvestLog,
    archive_harvested_dataservice,
    archive_harvested_dataset,
)
from ..signals import after_harvest_job, before_harvest_job

log = logging.getLogger(__name__)

# Disable those annoying warnings
requests.packages.urllib3.disable_warnings()


class HarvestFilter(object):
    TYPES = {
        str: "string",
        bytes: "string",
        int: "integer",
        bool: "boolean",
        UUID: "uuid",
        datetime: "date-time",
        date: "date",
    }

    def __init__(self, label, key, type, description=None):
        if type not in self.TYPES:
            raise TypeError("Unsupported type {0}".format(type))
        self.label = label
        self.key = key
        self.type = type
        self.description = description

    def as_dict(self):
        return {
            "label": self.label,
            "key": self.key,
            "type": self.TYPES[self.type],
            "description": self.description,
        }


class HarvestExtraConfig(HarvestFilter):
    pass


class HarvestFeature(object):
    def __init__(self, key, label, description=None, default=False):
        self.key = key
        self.label = label
        self.description = description
        self.default = default

    def as_dict(self):
        return {
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "default": self.default,
        }


class BaseBackend(object):
    """
    Base class that wrap children methods to add error management and debug logs.
    Also provides a few helpers needed on all or some backends.
    """

    name = None
    display_name = None
    verify_ssl = True

    # Define some allowed filters on the backend
    # This a Sequence[HarvestFilter]
    filters = tuple()

    # Define some allowed filters on the backend
    # This a Sequence[HarvestFeature]
    features = tuple()

    # Define some allowed extras config variables on the backend
    # This a Sequence[HarvestExtraConfig]
    extra_configs = tuple()

    def __init__(self, source_or_job, dryrun=False, max_items=None):
        if isinstance(source_or_job, HarvestJob):
            self.source = source_or_job.source
            self.job = source_or_job
        else:
            self.source = source_or_job
            self.job = None
        self.dryrun = dryrun
        self.max_items = max_items or current_app.config["HARVEST_MAX_ITEMS"]

    @property
    def config(self):
        return self.source.config

    def head(self, url, headers={}, **kwargs):
        headers.update(self.get_headers())
        kwargs["verify"] = kwargs.get("verify", self.verify_ssl)
        return requests.head(url, headers=headers, **kwargs)

    def get(self, url, headers={}, **kwargs):
        headers.update(self.get_headers())
        kwargs["verify"] = kwargs.get("verify", self.verify_ssl)
        return requests.get(url, headers=headers, **kwargs)

    def post(self, url, data, headers={}, **kwargs):
        headers.update(self.get_headers())
        kwargs["verify"] = kwargs.get("verify", self.verify_ssl)
        return requests.post(url, data=data, headers=headers, **kwargs)

    def get_headers(self):
        return {
            # TODO: extract site title and version
            "User-Agent": "uData/0.1 {0.name}".format(self),
        }

    def has_feature(self, key):
        try:
            feature = next(f for f in self.features if f.key == key)
        except StopIteration:
            raise HarvestException("Unknown feature {}".format(key))
        return self.config.get("features", {}).get(key, feature.default)

    def get_filters(self):
        return self.config.get("filters", [])

    def get_extra_config_value(self, key: str):
        extra_config = next(
            (c for c in self.config.get("extra_configs", []) if c["key"] == key), None
        )
        if extra_config:
            return extra_config["value"]

    def inner_harvest(self):
        raise NotImplementedError

    def inner_process_dataset(self, item: HarvestItem) -> Dataset:
        raise NotImplementedError

    def inner_process_dataservice(self, item: HarvestItem) -> Dataservice:
        raise NotImplementedError

    def harvest(self):
        log.debug(f"Starting harvesting {self.source.name} ({self.source.url})…")
        factory = HarvestJob if self.dryrun else HarvestJob.objects.create
        self.job = factory(status="initialized", started=datetime.utcnow(), source=self.source)

        before_harvest_job.send(self)

        try:
            self.inner_harvest()

            if self.source.autoarchive:
                self.autoarchive()

            self.job.status = "done"

            if any(i.status == "failed" for i in self.job.items):
                self.job.status += "-errors"
        except HarvestValidationError as e:
            log.exception(
                f'Harvesting validation failed for "{safe_unicode(self.source.name)}" ({self.source.backend})'
            )

            self.job.status = "failed"

            error = HarvestError(message=safe_unicode(e))
            self.job.errors.append(error)
        except Exception as e:
            log.exception(
                f'Harvesting failed for "{safe_unicode(self.source.name)}" ({self.source.backend})'
            )

            self.job.status = "failed"

            error = HarvestError(message=safe_unicode(e), details=traceback.format_exc())
            self.job.errors.append(error)
        finally:
            self.end_job()

        return self.job

    def process_dataset(self, remote_id: str, **kwargs):
        log.debug(f"Processing dataset {remote_id}…")

        # TODO add `type` to `HarvestItem` to differentiate `Dataset` from `Dataservice`
        item = HarvestItem(status="started", started=datetime.utcnow(), remote_id=remote_id)
        self.job.items.append(item)
        self.save_job()

        log_catcher = LogCatcher()

        try:
            if not remote_id:
                raise HarvestSkipException("missing identifier")

            current_app.logger.addHandler(log_catcher)
            dataset = self.inner_process_dataset(item, **kwargs)

            # Use `item.remote_id` because `inner_process_dataset` could have modified it.
            dataset.harvest = self.update_dataset_harvest_info(dataset.harvest, item.remote_id)
            dataset.archived = None

            # TODO: Apply editable mappings

            if self.dryrun:
                dataset.validate()
            else:
                dataset.save()
            item.dataset = dataset
            item.status = "done"
        except HarvestSkipException as e:
            item.status = "skipped"

            log.info(f"Skipped item {item.remote_id} : {safe_unicode(e)}")
            item.errors.append(HarvestError(message=safe_unicode(e)))
        except HarvestValidationError as e:
            item.status = "failed"

            log.info(f"Error validating item {item.remote_id} : {safe_unicode(e)}")
            item.errors.append(HarvestError(message=safe_unicode(e)))
        except Exception as e:
            item.status = "failed"
            log.exception(f"Error while processing {item.remote_id} : {safe_unicode(e)}")

            error = HarvestError(message=safe_unicode(e), details=traceback.format_exc())
            item.errors.append(error)
        finally:
            current_app.logger.removeHandler(log_catcher)
            item.ended = datetime.utcnow()
            item.logs = [
                HarvestLog(level=record.levelname, message=record.getMessage())
                for record in log_catcher.records
            ]
            self.save_job()

    def has_reached_max_items(self) -> bool:
        """Should be called after process_dataset to know if we reach the max items"""
        return self.max_items and len(self.job.items) >= self.max_items

    def process_dataservice(self, remote_id: str, **kwargs) -> bool:
        """
        Return `True` if the parent should stop iterating because we exceed the number
        of items to process.
        """
        log.debug(f"Processing dataservice {remote_id}…")

        # TODO add `type` to `HarvestItem` to differentiate `Dataset` from `Dataservice`
        item = HarvestItem(status="started", started=datetime.utcnow(), remote_id=remote_id)
        self.job.items.append(item)
        self.save_job()

        try:
            if not remote_id:
                raise HarvestSkipException("missing identifier")

            dataservice = self.inner_process_dataservice(item, **kwargs)

            dataservice.harvest = self.update_dataservice_harvest_info(
                dataservice.harvest, remote_id
            )
            dataservice.archived_at = None

            # TODO: Apply editable mappings

            if self.dryrun:
                dataservice.validate()
            else:
                dataservice.save()
            item.dataservice = dataservice
            item.status = "done"
        except HarvestSkipException as e:
            item.status = "skipped"

            log.info(f"Skipped item {item.remote_id} : {safe_unicode(e)}")
            item.errors.append(HarvestError(message=safe_unicode(e)))
        except HarvestValidationError as e:
            item.status = "failed"

            log.info(f"Error validating item {item.remote_id} : {safe_unicode(e)}")
            item.errors.append(HarvestError(message=safe_unicode(e)))
        except Exception as e:
            item.status = "failed"
            log.exception(f"Error while processing {item.remote_id} : {safe_unicode(e)}")

            error = HarvestError(message=safe_unicode(e), details=traceback.format_exc())
            item.errors.append(error)
        finally:
            item.ended = datetime.utcnow()
            self.save_job()

    def update_dataset_harvest_info(self, harvest: HarvestDatasetMetadata | None, remote_id: int):
        if not harvest:
            harvest = HarvestDatasetMetadata()

        harvest.backend = self.display_name
        harvest.source_id = str(self.source.id)
        harvest.remote_id = remote_id
        harvest.domain = self.source.domain
        harvest.last_update = datetime.utcnow()
        harvest.archived_at = None
        harvest.archived = None

        # created_at, modified_at, remote_url, uri, dct_identifier are set in `dataset_from_rdf`

        return harvest

    def update_dataservice_harvest_info(
        self, harvest: HarvestDataserviceMetadata | None, remote_id: int
    ):
        if not harvest:
            harvest = HarvestDataserviceMetadata()

        harvest.backend = self.display_name
        harvest.domain = self.source.domain

        harvest.source_id = str(self.source.id)
        harvest.source_url = str(self.source.url)

        harvest.remote_id = remote_id
        harvest.last_update = datetime.utcnow()

        harvest.archived_at = None
        harvest.archived_reason = None

        return harvest

    def save_job(self):
        if not self.dryrun:
            self.job.save()

    def end_job(self):
        self.job.ended = datetime.utcnow()
        if not self.dryrun:
            self.job.save()

        after_harvest_job.send(self)

    def autoarchive(self):
        """
        Archive items that exist on the local instance but not on remote platform
        after a grace period of HARVEST_AUTOARCHIVE_GRACE_DAYS days.
        """
        log.debug("Running autoarchive")
        limit_days = current_app.config["HARVEST_AUTOARCHIVE_GRACE_DAYS"]
        limit_date = date.today() - timedelta(days=limit_days)
        remote_ids = [i.remote_id for i in self.job.items if i.status != "archived"]
        q = {
            "harvest__source_id": str(self.source.id),
            "harvest__remote_id__nin": remote_ids,
            "harvest__last_update__lt": limit_date,
        }
        local_datasets_not_on_remote = Dataset.objects.filter(**q)
        local_dataservices_not_on_remote = Dataservice.objects.filter(**q)

        for dataset in local_datasets_not_on_remote:
            if not dataset.harvest.archived_at:
                archive_harvested_dataset(dataset, reason="not-on-remote", dryrun=self.dryrun)
            # add a HarvestItem to the job list (useful for report)
            # even when archiving has already been done (useful for debug)
            self.job.items.append(
                HarvestItem(
                    remote_id=str(dataset.harvest.remote_id), dataset=dataset, status="archived"
                )
            )

            self.save_job()

        for dataservice in local_dataservices_not_on_remote:
            if not dataservice.harvest.archived_at:
                archive_harvested_dataservice(
                    dataservice, reason="not-on-remote", dryrun=self.dryrun
                )
            # add a HarvestItem to the job list (useful for report)
            # even when archiving has already been done (useful for debug)
            self.job.items.append(
                HarvestItem(
                    remote_id=str(dataservice.harvest.remote_id),
                    dataservice=dataservice,
                    status="archived",
                )
            )

            self.save_job()

    def get_dataset(self, remote_id):
        """Get or create a dataset given its remote ID (and its source)
        We first try to match `source_id` to be source domain independent
        """
        try:
            uris.validate(remote_id)
            dataset = Dataset.objects(harvest__remote_id=remote_id).first()
        except uris.ValidationError:
            dataset = Dataset.objects(
                __raw__={
                    "harvest.remote_id": remote_id,
                    "$or": [
                        {"harvest.domain": self.source.domain},
                        {"harvest.source_id": str(self.source.id)},
                    ],
                }
            ).first()

        if dataset:
            return dataset

        if self.source.organization:
            return Dataset(organization=self.source.organization)
        elif self.source.owner:
            return Dataset(owner=self.source.owner)

        return Dataset()

    def get_dataservice(self, remote_id):
        """Get or create a dataservice given its remote ID (and its source)
        We first try to match `source_id` to be source domain independent
        """
        dataservice = Dataservice.objects(
            __raw__={
                "harvest.remote_id": remote_id,
                "$or": [
                    {"harvest.domain": self.source.domain},
                    {"harvest.source_id": str(self.source.id)},
                ],
            }
        ).first()

        if dataservice:
            return dataservice

        if self.source.organization:
            return Dataservice(organization=self.source.organization)
        elif self.source.owner:
            return Dataservice(owner=self.source.owner)

        return Dataservice()

    def validate(self, data, schema):
        """Perform a data validation against a given schema.

        :param data: an object to validate
        :param schema: a Voluptous schema to validate against
        """
        try:
            return schema(data)
        except MultipleInvalid as ie:
            errors = []
            for error in ie.errors:
                if error.path:
                    field = ".".join(str(p) for p in error.path)
                    path = error.path
                    value = data
                    while path:
                        attr = path.pop(0)
                        try:
                            if isinstance(value, (list, tuple)):
                                attr = int(attr)
                            value = value[attr]
                        except Exception:
                            value = None

                    txt = safe_unicode(error).replace("for dictionary value", "")
                    txt = txt.strip()
                    if isinstance(error, RequiredFieldInvalid):
                        msg = "[{0}] {1}"
                    else:
                        msg = "[{0}] {1}: {2}"
                    try:
                        msg = msg.format(field, txt, str(value))
                    except Exception:
                        msg = "[{0}] {1}".format(field, txt)

                else:
                    msg = str(error)
                errors.append(msg)
            msg = "\n- ".join(["Validation error:"] + errors)
            raise HarvestValidationError(msg)


class LogCatcher(logging.Handler):
    records: list[logging.LogRecord]

    def __init__(self):
        self.records = []
        super().__init__()

    def emit(self, record):
        self.records.append(record)
