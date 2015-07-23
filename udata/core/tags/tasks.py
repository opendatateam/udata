# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging

from udata.models import Dataset, Reuse
from udata.tasks import job

from .models import Tag

log = logging.getLogger(__name__)

map_tags = '''
function() {
    this.tags.forEach(function(tag) {
        emit(tag, 1);
    });
}
'''

reduce_tags = '''
function(key, values) {
    var total = 0;
    for(var i = 0; i < values.length; i++) {
        total += values[i];
    }
    return total;
}
'''

TAGGED = {
    'datasets': Dataset,
    'reuses': Reuse,
}


@job('count-tags')
def count_tags(self):
    '''Count tag occurences by type and update the tag collection'''
    for key, model in TAGGED.items():
        collection = '{0}_tags'.format(key)
        results = (model.objects(tags__exists=True)
                        .map_reduce(map_tags, reduce_tags, collection))
        for result in results:
            tag, created = Tag.objects.get_or_create(name=result.key,
                                                     auto_save=False)
            tag.counts[key] = int(result.value) if result.value else 0
            tag.save()
