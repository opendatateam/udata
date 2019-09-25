import pytest

from flask import Blueprint, render_template_string, url_for
from udata.frontend import template_hook
from udata.tests.helpers import assert200

bp = Blueprint('hooks_tests', __name__, url_prefix='/hooks_tests')


@template_hook
def single(ctx):
    return 'single'


@template_hook('multiple')
def first(ctx):
    return 'first'


@template_hook('multiple')
def second(ctx):
    return 'second'


@bp.route('/empty/render')
def render_empty():
    return render_template_string('{{ hook("siemptyngle") }}')


@bp.route('/empty/iter')
def iter_empty():
    return render_template_string('{% for w in hook("empty") %}<{{ w }}>{% endfor %}')


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
