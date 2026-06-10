import logging

from .markdown import init_app as init_markdown

log = logging.getLogger(__name__)


def init_app(app):
    init_markdown(app)
