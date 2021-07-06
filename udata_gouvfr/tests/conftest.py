import sys
import pytest


@pytest.fixture(autouse=True)
def _load_theme(request, _configure_application):
    if 'app' not in request.fixturenames:
        return

    app = request.getfixturevalue('app')
    # marker = request.node.get_closest_marker('frontend')
    # modules = set(marker.args[0] if marker and marker.args else [])
    # if getattr(request.cls, 'modules', None):
    #     modules |= set(request.cls.modules)

    # if marker or hasattr(request.cls, 'modules'):
    #     from udata import frontend, api
    #     api.init_app(app)
    #     frontend.init_app(app, modules)

    if app.config['THEME'] != 'default':
        # Unload theme to allow multiple run with initialization
        from udata_gouvfr import theme
        with app.app_context():
            theme_module = theme.current.entrypoint.module_name

        def unload_theme():
            if theme_module in sys.modules:
                del sys.modules[theme_module]
        request.addfinalizer(unload_theme)
