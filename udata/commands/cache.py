import logging

from udata.app import cache
from udata.commands import cli, success

log = logging.getLogger(__name__)


@cli.group("cache")
def grp():
    """
    Cache related operations.
    """
    pass


@grp.command()
def flush():
    """Flush the cache"""
    log.info("Flushing cache")
    cache.clear()
    success("Cache flushed")
