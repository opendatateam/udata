import pytest

from datetime import date

from flask import url_for, render_template_string, g, Blueprint

from udata.i18n import I18nBlueprint
from udata.models import db
from udata.tests.helpers import assert_urls_equal, full_url
from udata_front.frontend.helpers import in_url
from udata_front.tests import GouvFrSettings


def iso2date(string):
    return date(*[int(v) for v in string.split('-')])


def dr(start, end, **kwargs):
    return db.DateRange(start=iso2date(start), end=iso2date(end), **kwargs)


@pytest.mark.usefixtures('app')
@pytest.mark.frontend
class FrontEndRootTest:
    settings = GouvFrSettings

    def test_rewrite(self, app):
        '''url_rewrite should replace a parameter in the URL if present'''
        url = url_for('site.home', one='value', two='two')
        expected = full_url('site.home', one='other-value', two=2)

        with app.test_request_context(url):
            result = render_template_string(
                "{{ url_rewrite(one='other-value', two=2) }}")

        assert_urls_equal(result, expected)

    def test_rewrite_append(self, app):
        '''url_rewrite should replace a parameter in the URL if present'''
        url = url_for('site.home')
        expected = full_url('site.home', one='value')

        with app.test_request_context(url):
            result = render_template_string("{{ url_rewrite(one='value') }}")

        assert_urls_equal(result, expected)

    def test_url_add(self):
        '''url_add should add a parameter to the URL'''
        url = url_for('site.home', one='value')

        result = render_template_string(
            "{{ url|url_add(two='other') }}", url=url)

        assert_urls_equal(result,
                          url_for('site.home', one='value', two='other'))

    def test_url_add_append(self):
        '''url_add should add a parameter to the URL even if exists'''
        url = url_for('site.home', one='value')
        expected = url_for('site.home', one=['value', 'other-value'])

        result = render_template_string(
            "{{ url|url_add(one='other-value') }}", url=url)

        assert_urls_equal(result, expected)

    def test_url_del_by_name(self):
        '''url_del should delete a parameter by name from the URL'''
        url = url_for('site.home', one='value', two='other')
        expected = url_for('site.home', two='other')

        result = render_template_string("{{ url|url_del('one') }}", url=url)

        assert_urls_equal(result, expected)

    def test_url_del_by_value(self):
        '''url_del should delete a parameter by value from the URL'''
        url = url_for('site.home', one=['value', 'other-value'], two='other')
        expected = url_for('site.home', one='value', two='other')

        result = render_template_string(
            "{{ url|url_del(one='other-value') }}", url=url)

        assert_urls_equal(result, expected)

    def test_url_del_by_value_not_string(self):
        '''url_del should delete a parameter by value from the URL'''
        url = url_for('site.home', one=['value', 42], two='other')
        expected = url_for('site.home', one='value', two='other')

        result = render_template_string("{{ url|url_del(one=42) }}", url=url)

        assert_urls_equal(result, expected)

    def test_args_in_url(self, app):
        '''in_url() should test the presence of a key in url'''
        url = url_for('site.home', key='value', other='other')

        with app.test_request_context(url):
            assert in_url('key')
            assert in_url('other')
            assert in_url('key', 'other')
            assert not in_url('fake')
            assert not in_url('key', 'fake')

    def test_kwargs_in_url(self, app):
        '''in_url() should test the presence of key/value pair in url'''
        url = url_for('site.home', key='value', other='other')

        with app.test_request_context(url):
            assert in_url(key='value')
            assert in_url(key='value', other='other')
            assert not in_url(key='other')
            assert not in_url(key='value', other='value')

            assert in_url('other', key='value')

    def test_as_filter(self):
        '''URL helpers should exists as filter'''
        url = url_for('site.home', one='value')

        assert_urls_equal(
            render_template_string(
                "{{ url|url_rewrite(one='other-value') }}", url=url),
            url_for('site.home', one='other-value')
        )
        assert_urls_equal(
            render_template_string(
                "{{ url|url_add(two='other-value') }}", url=url),
            url_for('site.home', one='value', two='other-value')
        )
        assert_urls_equal(
            render_template_string("{{ url|url_del('one') }}", url=url),
            url_for('site.home')
        )

    def test_as_global(self):
        '''URL helpers should exists as global function'''
        url = url_for('site.home', one='value')

        assert_urls_equal(
            render_template_string(
                "{{ url_rewrite(url, one='other-value') }}", url=url),
            url_for('site.home', one='other-value')
        )
        assert_urls_equal(
            render_template_string(
                "{{ url_add(url, two='other-value') }}", url=url),
            url_for('site.home', one='value', two='other-value')
        )
        assert_urls_equal(
            render_template_string("{{ url_del(url, 'one') }}", url=url),
            url_for('site.home')
        )

    def test_as_global_default(self, app):
        '''URL helpers should exists as global function without url param'''
        url = url_for('site.home', one='value')

        with app.test_request_context(url):
            assert_urls_equal(
                render_template_string("{{ url_rewrite(one='other-value') }}"),
                full_url('site.home', one='other-value')
            )
            assert_urls_equal(
                render_template_string("{{ url_add(two='other-value') }}"),
                full_url('site.home', one='value', two='other-value')
            )
            assert_urls_equal(
                render_template_string("{{ url_del(None, 'one') }}"),
                full_url('site.home')
            )
            assert render_template_string("{{ in_url('one') }}") == 'True'
            assert render_template_string("{{ in_url('one') }}") == 'True'
            assert render_template_string("{{ in_url('two') }}") == 'False'

    @pytest.mark.parametrize('dates,expected', (
        (('2014-02-01', '2014-02-01'), '2014'),
        (('2012-01-01', '2012-01-31'), '2012'),
        (('2012-01-01', '2012-01-14'), '2012'),
        (('2012-01-01', '2012-03-31'), '2012'),
        (('2012-01-01', '2012-02-29'), '2012'),
        (('2012-01-01', '2012-12-31'), '2012'),
        (('2012-01-01', '2014-12-31'), '2012–2014'),
        (('2012-02-02', '2014-12-25'), '2012–2014'),
        # Before 1900
        (('1234-02-01', '1234-02-01'), '1234'),
        (('1232-01-01', '1232-01-31'), '1232'),
        (('1232-01-01', '1232-01-14'), '1232'),
        (('1232-01-01', '1232-03-31'), '1232'),
        (('1232-01-01', '1232-02-29'), '1232'),
        (('1232-01-01', '1232-12-31'), '1232'),
        (('1232-01-01', '1234-12-31'), '1232–1234'),
        (('1232-02-02', '1234-12-25'), '1232–1234'),
    ))
    def test_daterange(self, dates, expected):
        '''Daterange filter should display range in an adaptive'''
        g.lang_code = 'en'
        tpl = '{{dates|daterange}}'

        assert render_template_string(tpl, dates=dr(*dates)) == expected

    @pytest.mark.parametrize('dates,expected', (
        (('2014-02-01', '2014-02-01'), '2014/02/01'),
        (('2012-01-01', '2012-01-31'), '2012/01'),
        (('2012-01-01', '2012-01-14'), '2012/01/01 to 2012/01/14'),
        (('2012-01-01', '2012-03-31'), '2012/01 to 2012/03'),
        (('2012-01-01', '2012-02-29'), '2012/01 to 2012/02'),
        (('2012-01-01', '2012-12-31'), '2012'),
        (('2012-01-01', '2014-12-31'), '2012 to 2014'),
        (('2012-02-02', '2014-12-25'), '2012/02/02 to 2014/12/25'),
        # Before 1900
        (('1234-02-01', '1234-02-01'), '1234/02/01'),
        (('1232-01-01', '1232-01-31'), '1232/01'),
        (('1232-01-01', '1232-01-14'), '1232/01/01 to 1232/01/14'),
        (('1232-01-01', '1232-03-31'), '1232/01 to 1232/03'),
        (('1232-01-01', '1232-02-29'), '1232/01 to 1232/02'),
        (('1232-01-01', '1232-12-31'), '1232'),
        (('1232-01-01', '1234-12-31'), '1232 to 1234'),
        (('1232-02-02', '1234-12-25'), '1232/02/02 to 1234/12/25'),
    ))
    def test_daterange_with_details(self, dates, expected):
        '''Daterange filter should display range in an adaptive'''
        g.lang_code = 'en'
        tpl = '{{dates|daterange(details=True)}}'

        assert render_template_string(tpl, dates=dr(*dates)) == expected

    def test_daterange_bad_type(self):
        '''Daterange filter should only accept db.DateRange as parameter'''
        with pytest.raises(ValueError):
            render_template_string('{{"value"|daterange}}')

    def test_ficon(self):
        '''Should render a font-awesome icon class'''
        assert render_template_string('{{ficon("icon")}}') == 'fa fa-icon'
        assert render_template_string('{{ficon("fa-icon")}}') == 'fa fa-icon'

    def test_i18n_alternate_links(self, app, client):
        test = I18nBlueprint('test', __name__)

        @test.route('/i18n/<key>/')
        def i18n(key):
            return render_template_string('{{ i18n_alternate_links() }}')

        app.register_blueprint(test)
        app.config['DEFAULT_LANGUAGE'] = 'en'
        app.config['LANGUAGES'] = {
            'en': 'English',
            'fr': 'Français',
            'de': 'German',
        }

        response = client.get(url_for('test.i18n', key='value', param='other'))
        link = ('<link rel="alternate" '
                'href="/{lang}/i18n/value/?param=other" '
                'hreflang="{lang}" />')
        assert response.data.decode('utf8') == ''.join([link.format(lang='fr'),
                                                        link.format(lang='de')])

    def test_i18n_alternate_links_outside_i18n_blueprint(self, app, client):
        test = Blueprint('test', __name__)

        @test.route('/not-i18n/<key>/')
        def i18n(key):
            return render_template_string('{{ i18n_alternate_links() }}')

        app.register_blueprint(test)
        app.config['DEFAULT_LANGUAGE'] = 'en'
        app.config['LANGUAGES'] = {
            'en': 'English',
            'fr': 'Français',
            'de': 'German',
        }

        response = client.get(url_for('test.i18n', key='value', param='other'))
        assert response.data == b''
