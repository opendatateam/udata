# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import Dataset, TerritorialCoverage

# Ensure territories are registered
from . import territories  # noqa

# TODO: service_public flag as an extension

#TODO Remove territorial coverage from core
Dataset.extras.register('territorial_coverage', TerritorialCoverage)
