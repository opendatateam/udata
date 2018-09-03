# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging

from udata.frontend import csv
from udata.i18n import I18nBlueprint

from .csv import TagCsvAdapter
from .models import Tag

log = logging.getLogger(__name__)


blueprint = I18nBlueprint('tags', __name__)


@blueprint.route('/tags.csv', endpoint='csv', cors=True)
def tags_csv():
    adapter = TagCsvAdapter(Tag.objects.order_by('-total'))
    return csv.stream(adapter, 'tags')
