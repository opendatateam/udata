import logging
from datetime import datetime

from flask import current_app

from udata.entrypoints import get_enabled

log = logging.getLogger(__name__)


ENTRYPOINT = 'udata.linkcheckers'


class NoCheckLinkchecker(object):
    """Dummy linkchecker for resources that need no check"""

    def check(self, _):
        return {
            'check:status': 204,
            'check:available': True,
            'check:date': datetime.now()
        }


def get(name):
    '''Get a linkchecker given its name or fallback on default'''
    linkcheckers = get_enabled(ENTRYPOINT, current_app)
    linkcheckers.update(no_check=NoCheckLinkchecker)  # no_check always enabled
    selected_linkchecker = linkcheckers.get(name)
    if not selected_linkchecker:
        default_linkchecker = current_app.config.get(
                                'LINKCHECKING_DEFAULT_LINKCHECKER')
        selected_linkchecker = linkcheckers.get(default_linkchecker)
    if not selected_linkchecker:
        log.error('No linkchecker found ({} requested and no fallback)'.format(
                  name))
    return selected_linkchecker
