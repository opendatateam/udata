import logging
import traceback
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Concatenate, Never, ParamSpec, TypeVar, Union
from uuid import UUID

import requests
from bson import ObjectId
from flask import current_app, g
from voluptuous import MultipleInvalid, RequiredFieldInvalid

import udata.uris as uris
from udata.core.dataservices.models import Dataservice
from udata.core.dataservices.models import HarvestMetadata as HarvestDataserviceMetadata
from udata.core.dataset.models import Dataset, HarvestDatasetMetadata
from udata.core.user.models import User
from udata.utils import raise_if_redirect, safe_unicode

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


Harvestable = TypeVar("Harvestable", bound=Union[Dataset, Dataservice])
HarvestMetadata = TypeVar(
    "HarvestMetadata", bound=Union[HarvestDatasetMetadata, HarvestDataserviceMetadata]
)

ItemProcessorParams = ParamSpec("ItemProcessorParams")


class BaseBackend(ABC):
    """
    Base class that wrap children methods to add error management and debug logs.
    Also provides a few helpers needed on all or some backends.
    """

    name: str
    display_name: str | None = None
    verify_ssl = True

    # When False (default), GET, HEAD, and POST requests will raise a
    # HTTPError on any 3xx response. Override to True to permit redirects.
    allow_redirects = False

    # Define some allowed filters on the backend
    # This a Sequence[HarvestFilter]
    # Filters are public, don't store sensitive information
    filters = tuple()

    # Define some allowed filters on the backend
    # This a Sequence[HarvestFeature]
    features = tuple()

    # Define some allowed extras config variables on the backend
    # This a Sequence[HarvestExtraConfig]
    # Extra configs are public, don't store sensitive information
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
        kwargs["allow_redirects"] = kwargs.get("allow_redirects", self.allow_redirects)
        response = requests.head(url, headers=headers, **kwargs)
        if not kwargs["allow_redirects"]:
            raise_if_redirect(response)
        return response

    def get(self, url, headers={}, **kwargs):
        headers.update(self.get_headers())
        kwargs["verify"] = kwargs.get("verify", self.verify_ssl)
        kwargs["allow_redirects"] = kwargs.get("allow_redirects", self.allow_redirects)
        response = requests.get(url, headers=headers, **kwargs)
        if not kwargs["allow_redirects"]:
            raise_if_redirect(response)
        return response

    def post(self, url, data, headers={}, **kwargs):
        headers.update(self.get_headers())
        kwargs["verify"] = kwargs.get("verify", self.verify_ssl)
        kwargs["allow_redirects"] = kwargs.get("allow_redirects", self.allow_redirects)
        response = requests.post(url, data=data, headers=headers, **kwargs)
        if not kwargs["allow_redirects"]:
            raise_if_redirect(response)
        return response

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

    @abstractmethod
    def inner_harvest(self) -> Never:
        raise NotImplementedError

    def harvest(self) -> HarvestJob:
        log.debug(f"Starting harvesting {self.source.name} ({self.source.url})…")
        factory = HarvestJob if self.dryrun else HarvestJob.objects.create
        self.job = factory(status="initialized", started=datetime.now(UTC), source=self.source)
        self.remote_ids = set()

        before_harvest_job.send(self)
        # Set harvest_activity_user on global context during the run
        if current_app.config["HARVEST_ACTIVITY_USER_ID"]:
            try:
                # Try to fetch the existing harvest activity user
                g.harvest_activity_user = User.objects.get(
                    id=current_app.config["HARVEST_ACTIVITY_USER_ID"]
                )
            except User.DoesNotExist:
                log.exception(
                    "HARVEST_ACTIVITY_USER_ID does not seem to match an existing user id."
                )

        try:
            self.inner_harvest()

            if self.source.autoarchive:
                self.autoarchive()

            self.job.status = "done"

            if any(i.status == "failed" for i in self.job.items):
                self.job.status += "-errors"

        except HarvestValidationError as e:
            self.job.status = "failed"
            log.exception(
                f'Harvesting validation failed for "{safe_unicode(self.source.name)}" ({self.source.backend})'
            )
            error = HarvestError(message=safe_unicode(e))
            self.job.errors.append(error)

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.job.status = "failed"
            log.warning(
                f'Harvesting connection error for "{safe_unicode(self.source.name)}" ({self.source.backend}): {e}'
            )
            error = HarvestError(message=safe_unicode(e), details=traceback.format_exc())
            self.job.errors.append(error)

        except Exception as e:
            self.job.status = "failed"
            log.exception(
                f'Harvesting failed for "{safe_unicode(self.source.name)}" ({self.source.backend})'
            )
            error = HarvestError(message=safe_unicode(e), details=traceback.format_exc())
            self.job.errors.append(error)

        finally:
            self.end_job()
            # Clean harvest_activity_user on global context
            if hasattr(g, "harvest_activity_user"):
                delattr(g, "harvest_activity_user")

        return self.job

    def process_item(
        self,
        remote_id: str,
        item_processor: Callable[Concatenate[HarvestItem, ItemProcessorParams], Harvestable],
        *args: ItemProcessorParams.args,
        **kwargs: ItemProcessorParams.kwargs,
    ) -> Never:
        # FIXME: use typing.get_type_hints()["return"] or inspect.signature().return_annotation to get item type?
        log.debug(f"Processing item {remote_id}…")

        # TODO: add `type` to `HarvestItem` to differentiate `Dataset` from `Dataservice`
        harvest_item = self.add_harvest_item(
            HarvestItem(status="started", started=datetime.now(UTC), remote_id=remote_id)
        )

        log_catcher = LogCatcher()
        current_app.logger.addHandler(log_catcher)

        try:
            if not remote_id:
                raise HarvestSkipException("missing identifier")

            item = item_processor(harvest_item, *args, **kwargs)

            # IMPORTANT:
            # Use `harvest_item.remote_id` from this point, because `item_processor()` could have
            # modified it.

            # Update `remote_url` right away so it's available even if later code raises
            harvest_item.remote_url = item.harvest.remote_url

            self.ensure_unique_remote_id(harvest_item)

            item.harvest = self.update_harvest_metadata(item.harvest, harvest_item.remote_id)
            item.archived_at = None

            # TODO: Apply editable mappings

            if self.dryrun:
                item.validate()
                # A preview never saves, so the dataset would keep no pk and could not
                # be referenced by a dataservice harvested in the same run. Give it the
                # client-side id that save() would have generated so cross-references
                # between previewed objects stay valid and distinct.
                if isinstance(item, Dataset) and item.pk is None:
                    # FIXME: needed for dataservice?
                    item.id = ObjectId()
            else:
                item.save()

            # FIXME: why use a different field for different type?
            if isinstance(item, Dataset):
                harvest_item.dataset = item
            else:
                harvest_item.dataservice = item

            harvest_item.status = "done"

        except HarvestSkipException as e:
            harvest_item.status = "skipped"
            log.info(f"Skipped item {harvest_item.remote_id} : {safe_unicode(e)}")
            harvest_item.errors.append(HarvestError(message=safe_unicode(e)))

        except HarvestValidationError as e:
            harvest_item.status = "failed"
            log.info(f"Error validating item {harvest_item.remote_id} : {safe_unicode(e)}")
            harvest_item.errors.append(HarvestError(message=safe_unicode(e)))

        except Exception as e:
            harvest_item.status = "failed"
            log.exception(f"Error while processing {harvest_item.remote_id} : {safe_unicode(e)}")
            error = HarvestError(message=safe_unicode(e), details=traceback.format_exc())
            harvest_item.errors.append(error)

        finally:
            current_app.logger.removeHandler(log_catcher)
            harvest_item.ended = datetime.now(UTC)
            harvest_item.logs = [
                HarvestLog(level=record.levelname, message=record.getMessage())
                for record in log_catcher.records
            ]
            self.save_job()

    def has_reached_max_items(self) -> bool:
        """Should be called after process_item to know if we reach the max items"""
        return self.max_items and len(self.job.items) >= self.max_items

    def ensure_unique_remote_id(self, harvest_item: HarvestItem) -> Never:
        if harvest_item.remote_id in self.remote_ids:
            raise HarvestValidationError(f"Identifier '{harvest_item.remote_id}' already exists")

        self.remote_ids.add(harvest_item.remote_id)

    def update_harvest_metadata(self, metadata: HarvestMetadata, remote_id: str) -> HarvestMetadata:
        metadata.backend = self.display_name or "unknown"
        metadata.source_id = str(self.source.id)
        if hasattr(metadata, "source_url"):
            # FIXME: consolidate source_url to all HarvestMetadata (or remove)
            metadata.source_url = str(self.source.url)
        metadata.remote_id = remote_id
        metadata.domain = self.source.domain
        metadata.last_update = datetime.now(UTC)
        metadata.archived_at = None
        metadata.archived_reason = None

        # created_at, modified_at, remote_url, uri, dct_identifier are set in `*_from_rdf`

        return metadata

    def add_harvest_item(self, harvest_item: HarvestItem) -> HarvestItem:
        self.job.items.append(harvest_item)
        self.save_job()
        return harvest_item

    def save_job(self) -> Never:
        if not self.dryrun:
            self.job.save()

    def end_job(self) -> Never:
        self.job.ended = datetime.now(UTC)
        if not self.dryrun:
            self.job.save()
        after_harvest_job.send(self)

    def autoarchive(self) -> Never:
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
            self.add_harvest_item(
                HarvestItem(
                    remote_id=str(dataset.harvest.remote_id), dataset=dataset, status="archived"
                )
            )

        for dataservice in local_dataservices_not_on_remote:
            if not dataservice.harvest.archived_at:
                archive_harvested_dataservice(
                    dataservice, reason="not-on-remote", dryrun=self.dryrun
                )
            # add a HarvestItem to the job list (useful for report)
            # even when archiving has already been done (useful for debug)
            self.add_harvest_item(
                HarvestItem(
                    remote_id=str(dataservice.harvest.remote_id),
                    dataservice=dataservice,
                    status="archived",
                )
            )

    def get_item(self, remote_id: str, item_class: type[Harvestable]) -> Harvestable:
        """Get or create a `item_class` given its remote ID (and its source)
        We first try to match `source_id` to be source domain independent
        """
        try:
            uris.validate(remote_id)
            item = item_class.objects(harvest__remote_id=remote_id).first()
        except uris.ValidationError:
            item = item_class.objects(
                __raw__={
                    "harvest.remote_id": remote_id,
                    "$or": [
                        {"harvest.domain": self.source.domain},
                        {"harvest.source_id": str(self.source.id)},
                    ],
                }
            ).first()

        if item:
            self.ensure_unique_ownership(item)
        elif self.source.organization:
            item = item_class(organization=self.source.organization)
        elif self.source.owner:
            item = item_class(owner=self.source.owner)
        else:
            item = item_class()

        item.set_harvested()

        return item

    def ensure_unique_ownership(self, item: Harvestable) -> Never:
        """Raise if item already belongs to some other owner.

        Ressources (datasets, services, ...) must have universally unique
        identifiers, but some catalogs fail to enforce it. Cases seen
        in the wild:
        - Copy-pasting record metadata without changing the identifier.
        - Using the table name of the originating data as identifier, and
          generating several datasets out of the same table.
        - "TODO", "A REMPLIR", etc. in the identifier field.
        """
        other_owner = None
        if item.organization and item.organization != self.source.organization:
            other_owner = item.organization
        elif item.owner and item.owner != self.source.owner:
            other_owner = item.owner

        if other_owner:
            raise HarvestValidationError(
                f"Item has another owner: {other_owner.page() or other_owner.id}"
            )

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
