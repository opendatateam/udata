import logging

from click import echo
from flask import current_app

from udata.commands import KO, OK, cli, green, red, white

log = logging.getLogger(__name__)


@cli.group("info")
def grp():
    """Display some details about the local environment"""
    pass


def by_name(e):
    return e.name


def is_active(ep, actives):
    return green(OK) if ep.name in actives else red(KO)


@grp.command()
def config():
    """Display some details about the local configuration"""
    if hasattr(current_app, "settings_file"):
        log.info("Loaded configuration from %s", current_app.settings_file)

    log.info(white("Current configuration"))
    for key in sorted(current_app.config):
        if key.startswith("__") or not key.isupper():
            continue
        echo("{0}: {1}".format(white(key), current_app.config[key]))
