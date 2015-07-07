# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.i18n import lazy_gettext as _
from udata.models import Organization, PUBLIC_SERVICE
from udata.core.site.metrics import SiteMetric


__all__ = ('PublicServicesMetric', )


class PublicServicesMetric(SiteMetric):
    name = 'public_services'
    display_name = _('Public services')

    def get_value(self):
        return Organization.objects(badges__kind=PUBLIC_SERVICE).count()

PublicServicesMetric.connect(Organization.on_update)
