from jinja2 import Markup, contextfunction

from udata.i18n import I18nBlueprint

blueprint = I18nBlueprint('hooks', __name__)

_template_hooks = {}

def _wrapper(func, name=None, when=None):
    name = name or func.__name__
    if name not in _template_hooks:
        _template_hooks[name] = []
    _template_hooks[name].append((func, when))
    return func


def template_hook(func_or_name, when=None):
    if callable(func_or_name):
        return _wrapper(func_or_name)
    elif isinstance(func_or_name, str):
        def wrapper(func):
            return _wrapper(func, func_or_name, when=when)
        return wrapper


def has_template_hook(name):
    return name in _template_hooks


class HookRenderer:
    def __init__(self, funcs, ctx, *args, **kwargs):
        self.funcs = funcs
        self.ctx = ctx
        self.args = args
        self.kwargs = kwargs

    def __html__(self):
        return Markup(''.join(
            f(self.ctx, *self.args, **self.kwargs)
            for f, w in self.funcs
            if w is None or w(self.ctx)
        ))

    def __iter__(self):
        for func, when in self.funcs:
            if when is None or when(self.ctx):
                yield Markup(func(self.ctx, *self.args, **self.kwargs))


@contextfunction
def render_template_hook(ctx, name, *args, **kwargs):
    if not has_template_hook(name):
        return ''
    return HookRenderer(_template_hooks[name], ctx, *args, **kwargs)


@blueprint.app_context_processor
def inject_hooks():
    return {
        'hook': render_template_hook,
        'has_hook': has_template_hook,
    }

def init_app(app):
    app.register_blueprint(blueprint)
