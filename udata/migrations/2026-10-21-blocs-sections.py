"""
Move the blocs of posts, organizations and the site to sections, title blocs and grids.

Each top-level bloc goes into its own section, its title (or description for an accordion)
becomes a `TitleBloc`, and a list of datasets/reuses/dataservices becomes a grid with one
bloc per object. See `udata.core.edito_blocs.legacy`.

The lists could still hold objects hard-deleted before the purge reached them (it skipped
accordions until #3812): those are dropped, the bloc showing a single object requiring it.
"""

import logging

from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset
from udata.core.edito_blocs.legacy import legacy_references, upgrade_legacy_blocs
from udata.core.edito_blocs.models import SITE_BLOCS_FIELDS
from udata.core.organization.models import Organization
from udata.core.post.models import Post
from udata.core.reuse.models import Reuse
from udata.core.site.models import Site

log = logging.getLogger(__name__)


def existing(references: set) -> set:
    """The referenced ids still matching a dataset, a reuse or a dataservice."""
    if not references:
        return set()
    found = set()
    for model in (Dataset, Reuse, Dataservice):
        found.update(model._get_collection().distinct("_id", {"_id": {"$in": list(references)}}))
    return found


def migrate(db):
    for model, blocs_fields in (
        (Post, ("blocs",)),
        (Organization, ("presentation_blocs",)),
        (Site, SITE_BLOCS_FIELDS),
    ):
        collection = model._get_collection()
        for blocs_field in blocs_fields:
            # Already upgraded blocs fields only hold sections and heroes.
            legacy = {blocs_field: {"$elemMatch": {"_cls": {"$nin": ["SectionBloc", "HeroBloc"]}}}}
            count = dropped = 0
            for doc in collection.find(legacy, {blocs_field: 1}):
                references = legacy_references(doc[blocs_field])
                alive = existing(references)
                blocs = upgrade_legacy_blocs(doc[blocs_field], lambda ref: ref in alive)
                collection.update_one({"_id": doc["_id"]}, {"$set": {blocs_field: blocs}})
                count += 1
                dropped += len(references - alive)
            log.info(
                f"Upgraded {model.__name__}.{blocs_field} on {count} documents, "
                f"dropping {dropped} references to deleted objects"
            )
