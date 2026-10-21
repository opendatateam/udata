"""
Move the blocs of posts, organizations and the site to sections, title blocs and grids.

Each top-level bloc goes into its own section, its title (or description for an accordion)
becomes a `TitleBloc`, and a list of datasets/reuses/dataservices becomes a grid with one
bloc per object. See `udata.core.edito_blocs.legacy`.
"""

import logging

from udata.core.edito_blocs.legacy import upgrade_legacy_blocs
from udata.core.edito_blocs.models import SITE_BLOCS_FIELDS
from udata.core.organization.models import Organization
from udata.core.post.models import Post
from udata.core.site.models import Site

log = logging.getLogger(__name__)


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
            count = 0
            for doc in collection.find(legacy, {blocs_field: 1}):
                collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {blocs_field: upgrade_legacy_blocs(doc[blocs_field])}},
                )
                count += 1
            log.info(f"Upgraded {model.__name__}.{blocs_field} on {count} documents")
