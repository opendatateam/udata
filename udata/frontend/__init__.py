from .markdown import init_app as init_markdown


def init_app(app):
    init_markdown(app)
