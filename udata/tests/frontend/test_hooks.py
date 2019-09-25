import pytest

from flask import Blueprint, render_template_string, url_for
from udata.frontend import template_hook
from udata.tests.helpers import assert200

bp = Blueprint('hooks_tests', __name__, url_prefix='/hooks_tests')


@template_hook
def single(ctx):
    return 'single'


@template_hook
def hello(ctx, name):
    return 'Hello {}'.format(name)


@template_hook
def kwargs(ctx, **kwargs):
    return ', '.join(sorted('{0}={1}'.format(k, v) for k, v in kwargs.items()))


@template_hook('multiple')
def first(ctx):
    return 'first'


@template_hook('multiple')
def second(ctx):
    return 'second'


@template_hook('conditionnal', when=lambda ctx: True)
def true(ctx):
    return 'true'


@template_hook('conditionnal', when=lambda ctx: False)
def false(ctx):
    return 'false'


@bp.route('/empty/render')
def render_empty():
    return render_template_string('{{ hook("empty") }}')


@bp.route('/empty/iter')
def iter_empty():
    return render_template_string('{% for w in hook("empty") %}<{{ w }}>{% endfor %}')


@bp.route('/hello')
def render_hello():
    return render_template_string('{{ hook("hello", "world") }}')


@bp.route('/kwargs')
def render_kwargs():
    return render_template_string('{{ hook("kwargs", key="value", other=42) }}')


@bp.route('/single/render')
def render_single():
    return render_template_string('{{ hook("single") }}')


@bp.route('/single/iter')
def iter_single():
    return render_template_string('{% for w in hook("single") %}<{{ w }}>{% endfor %}')


@bp.route('/multiple/render')
def render_multiple():
    return render_template_string('{{ hook("multiple") }}')


@bp.route('/multiple/iter')
def iter_multiple():
    return render_template_string('{% for w in hook("multiple") %}<{{ w }}>{% endfor %}')


@bp.route('/conditionnal/render')
def render_conditionnal():
    return render_template_string('{{ hook("conditionnal") }}')


@bp.route('/conditionnal/iter')
def iter_conditionnal():
    return render_template_string('{% for w in hook("conditionnal") %}<{{ w }}>{% endfor %}')


@pytest.fixture
def app(app):
    app.register_blueprint(bp)
    return app


@pytest.mark.frontend
class HooksTest:
    def test_empty_template_hook(self, client):
        response = client.get(url_for('hooks_tests.render_empty'))
        assert200(response)
        assert b'' == response.data

    def test_iter_empty_template_hook(self, client):
        response = client.get(url_for('hooks_tests.iter_empty'))
        assert200(response)
        assert b'' == response.data

    def test_single_template_hook(self, client):
        response = client.get(url_for('hooks_tests.render_single'))
        assert200(response)
        assert b'single' == response.data

    def test_iter_single_template_hook(self, client):
        response = client.get(url_for('hooks_tests.iter_single'))
        assert200(response)
        assert b'<single>' == response.data

    def test_multiple_template_hooks(self, client):
        response = client.get(url_for('hooks_tests.render_multiple'))
        assert200(response)
        assert b'firstsecond' == response.data

    def test_iter_multiple_template_hooks(self, client):
        response = client.get(url_for('hooks_tests.iter_multiple'))
        assert200(response)
        assert b'<first><second>' == response.data

    def test_conditionnal_template_hooks(self, client):
        response = client.get(url_for('hooks_tests.render_conditionnal'))
        assert200(response)
        assert b'true' == response.data

    def test_iter_conditionnal_template_hooks(self, client):
        response = client.get(url_for('hooks_tests.iter_conditionnal'))
        assert200(response)
        assert b'<true>' == response.data

    def test_arguments(self, client):
        response = client.get(url_for('hooks_tests.render_hello'))
        assert200(response)
        assert b'Hello world' == response.data

    def test_kwargs(self, client):
        response = client.get(url_for('hooks_tests.render_kwargs'))
        assert200(response)
        assert b'key=value, other=42' == response.data
