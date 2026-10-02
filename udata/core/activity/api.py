import logging

from mongoengine.errors import DoesNotExist

from udata.api import API, api
from udata.core.dataset.permissions import OwnableReadPermission
from udata.core.owned import Owned
from udata.models import Activity

log = logging.getLogger(__name__)


@api.route("/activity/", endpoint="activity")
class SiteActivityAPI(API):
    @api.doc("activity")
    @api.expect(Activity.__index_parser__)
    @api.marshal_with(Activity.__page_fields__)
    def get(self):
        """Fetch site activity, optionally filtered by user or org."""
        qs = Activity.apply_sort_filters(Activity.objects)
        qs = Activity.apply_pagination(qs)

        # - Filter out DBRefs
        # Always return a result even not complete
        # But log the error (ie. visible in sentry, silent for user)
        # Can happen when someone manually delete an object in DB (ie. without proper purge)
        # - Filter out items not visible to the current user
        safe_items = []
        for item in qs.queryset.items:
            try:
                item.actor
                item.organization
                item.related_to
            except DoesNotExist as e:
                log.error(e, exc_info=True)
                continue

            if isinstance(item.related_to, Owned):
                if not OwnableReadPermission(item.related_to).can():
                    continue
            safe_items.append(item)
        qs.queryset.items = safe_items

        return qs
