import pytest

from bleach._vendor import html5lib
from flask import render_template_string

from udata.frontend.markdown import md, parse_html, EXCERPT_TOKEN
from udata.utils import faker

parser = html5lib.HTMLParser(tree=html5lib.getTreeBuilder("dom"))


def assert_md_equal(value, expected):
    __tracebackhide__ = True
    expected = '<div class="markdown">{0}</div>'.format(expected)
    assert value.strip() == expected


@pytest.fixture
def assert_md(app):
    def assertion(text, expected, url='/'):
        __tracebackhide__ = True
        with app.test_request_context(url):
            result = render_template_string('{{ text|markdown }}', text=text)
            assert_md_equal(result, expected)
    return assertion


@pytest.fixture
def md2dom(app):
    def helper(text, expected=None, url='/'):
        __tracebackhide__ = True
        with app.test_request_context(url):
            result = render_template_string('{{ text|markdown }}', text=text)
            if expected:
                assert_md_equal(result, expected)
            return parser.parse(result)
    return helper


@pytest.mark.frontend
class MarkdownTest:
    def test_excerpt_is_not_removed(self, app):
        with app.test_request_context('/'):
            assert_md_equal(md(EXCERPT_TOKEN), EXCERPT_TOKEN)

    def test_markdown_filter_with_none(self, app):
        '''Markdown filter should not fails with None'''
        text = None
        with app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)

        assert result == ''

    def test_markdown_links_nofollow(self, md2dom):
        '''Markdown filter should render links as nofollow'''
        text = '[example](http://example.net/ "Title")'
        dom = md2dom(text)
        el = dom.getElementsByTagName('a')[0]
        assert el.getAttribute('rel') == 'nofollow'
        assert el.getAttribute('href') == 'http://example.net/'
        assert el.getAttribute('title') == 'Title'
        assert el.firstChild.data == 'example'

    def test_markdown_linkify(self, md2dom):
        '''Markdown filter should transform urls to anchors'''
        text = 'http://example.net/'
        dom = md2dom(text)
        el = dom.getElementsByTagName('a')[0]
        assert el.getAttribute('rel') == 'nofollow'
        assert el.getAttribute('href') == 'http://example.net/'
        assert el.firstChild.data == 'http://example.net/'

    def test_markdown_autolink(self, md2dom):
        '''Markdown filter should transform urls to anchors'''
        text = '<http://example.net/>'
        dom = md2dom(text)
        el = dom.getElementsByTagName('a')[0]
        assert el.getAttribute('rel') == 'nofollow'
        assert el.getAttribute('href') == 'http://example.net/'
        assert el.firstChild.data == 'http://example.net/'

    def test_markdown_linkify_angle_brackets(self, md2dom):
        '''Markdown filter should transform urls to anchors'''
        text = '<http://example.net/path>'
        dom = md2dom(text)
        el = dom.getElementsByTagName('a')[0]
        assert el.getAttribute('rel') == 'nofollow'
        assert el.getAttribute('href') == 'http://example.net/path'
        assert el.firstChild.data == 'http://example.net/path'

    @pytest.mark.parametrize('link,expected', [
        ('/', 'http://local.test/'), ('bar', 'http://local.test/bar')
    ])
    def test_markdown_linkify_relative(self, md2dom, link, expected):
        '''Markdown filter should transform relative urls to external ones'''
        text = f'[foo]({link})'
        dom = md2dom(text)
        el = dom.getElementsByTagName('a')[0]
        assert el.getAttribute('rel') == ''
        assert el.getAttribute('href') == expected
        assert el.getAttribute('data-tooltip') == ''
        assert el.firstChild.data == 'foo'

    def test_markdown_linkify_https(self, md2dom):
        '''Markdown filter should transform relative urls with HTTPS'''
        text = '[foo](/foo)'
        dom = md2dom(text, url='https://local.test')
        el = dom.getElementsByTagName('a')[0]
        assert el.getAttribute('rel') == ''
        assert el.getAttribute('href') == 'https://local.test/foo'
        assert el.getAttribute('data-tooltip') == ''
        assert el.firstChild.data == 'foo'

    def test_markdown_linkify_ftp(self, md2dom):
        '''Markdown filter should transform ftp urls'''
        text = '[foo](ftp://random.net)'
        dom = md2dom(text)
        el = dom.getElementsByTagName('a')[0]
        assert el.getAttribute('href') == 'ftp://random.net'
        assert el.firstChild.data == 'foo'

    def test_markdown_linkify_relative_with_tooltip(self, app):
        '''Markdown filter should transform + add tooltip'''
        text = '[foo](/)'
        with app.test_request_context('/'):
            result = render_template_string(
                '{{ text|markdown(source_tooltip=True) }}', text=text)
            parsed = parser.parse(result)
            el = parsed.getElementsByTagName('a')[0]
            assert el.getAttribute('rel') == ''
            assert el.getAttribute('href') == 'http://local.test/'
            assert el.getAttribute('data-tooltip') == 'Source'
            assert el.firstChild.data == 'foo'

    def test_markdown_not_linkify_mails(self, md2dom):
        '''Markdown filter should not transform emails to anchors'''
        text = 'coucou@cmoi.fr'
        dom = md2dom(text, '<p>coucou@cmoi.fr</p>')
        assert dom.getElementsByTagName('a') == []

    def test_markdown_linkify_within_pre(self, assert_md):
        '''Markdown filter should not transform urls into <pre> anchors'''
        text = '<pre>http://example.net/</pre>'
        assert_md(text, '<pre>http://example.net/</pre>')

    def test_markdown_linkify_email_within_pre(self, assert_md):
        '''Markdown filter should not transform emails into <pre> anchors'''
        text = '<pre>coucou@cmoi.fr</pre>'
        assert_md(text, '<pre>coucou@cmoi.fr</pre>')

    def test_bleach_sanitize(self, assert_md):
        '''Markdown filter should sanitize evil code'''
        text = 'an <script>evil()</script>'
        assert_md(text, '<p>an &lt;script&gt;evil()&lt;/script&gt;</p>')

    def test_soft_break(self, assert_md):
        '''Markdown should treat soft breaks as br tag'''
        text = 'line 1\nline 2'
        assert_md(text, '<p>line 1<br>\nline 2</p>')

    def test_gfm_tables(self, assert_md):
        '''Should render GFM tables'''
        text = '\n'.join((
            '| first | second |',
            '|-------|--------|',
            '| value | value  |',
        ))
        expected = '\n'.join((
            '<table>',
            '<thead>',
            '<tr>',
            '<th>first</th>',
            '<th>second</th>',
            '</tr>',
            '</thead>',
            '<tbody>',
            '<tr>',
            '<td>value</td>',
            '<td>value</td>',
            '</tr>',
            '</tbody>',
            '</table>'
        ))
        assert_md(text, expected)

    def test_gfm_strikethrough(self, assert_md):
        '''Should render GFM strikethrough (extension)'''
        text = '~~Hi~~ Hello, world!'
        assert_md(text, '<p><del>Hi</del> Hello, world!</p>')

    def test_gfm_tagfilter(self, assert_md):
        '''It should handle GFM tagfilter extension'''
        # Test extracted from https://github.github.com/gfm/#disallowed-raw-html-extension-
        text = '\n'.join((
            '<strong> <title></title> <style></style> <em></em></strong>',
            '<blockquote>',
            '  <xmp> is disallowed.  <XMP> is also disallowed.',
            '</blockquote>',
        ))
        expected = '\n'.join((
            '<p><strong> &lt;title&gt;&lt;/title&gt; &lt;style&gt;&lt;/style&gt; <em></em></strong></p>',
            '<blockquote>',
            '  &lt;xmp&gt; is disallowed.  &lt;XMP&gt; is also disallowed.',
            '</blockquote>',
        ))
        assert_md(text, expected)

    def test_gfm_tagfilter_legit(self, assert_md):
        '''It should not filter legit markup'''
        text = '\n'.join((
            '> This is a blockquote',
            '> with <script>evil()</script> inside',
        ))
        expected = '\n'.join((
            '<blockquote><p>This is a blockquote<br>',
            'with &lt;script&gt;evil()&lt;/script&gt; inside</p>',
            '</blockquote>',
        ))
        assert_md(text, expected)


@pytest.mark.frontend
class MdStripTest:
    def test_mdstrip_filter(self, app):
        '''mdstrip should truncate the text before rendering'''
        text = '1 2 3 4 5 6 7 8 9 0'
        with app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip(7) }}', text=text)

        assert result == '1 2 3…'

    def test_mdstrip_filter_does_not_truncate_without_size(self, app):
        '''mdstrip should not truncate by default'''
        text = 'aaaa ' * 300
        with app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip }}', text=text)

        assert result.strip() == text.strip()

    def test_mdstrip_filter_with_none(self, app):
        '''mdstrip filter should not fails with None'''
        text = None
        with app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip }}', text=text)

        assert result == ''

    def test_mdstrip_filter_with_excerpt(self, app):
        '''mdstrip should truncate on token if shorter than required size'''
        text = ''.join(['excerpt', EXCERPT_TOKEN, 'aaaa ' * 10])
        with app.test_request_context('/'):
            result = render_template_string(
                '{{ text|mdstrip(20) }}', text=text)

        assert result == 'excerpt'

    def test_mdstrip_does_not_truncate_in_tags(self, app):
        '''mdstrip should not truncate in middle of a tag'''
        text = '![Legend](http://www.somewhere.com/image.jpg) Here. aaaaa'
        with app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip(5) }}', text=text)

        assert result.strip() == 'Here…'

    def test_mdstrip_returns_unsafe_string(self, app):
        '''mdstrip should returns html compliants strings'''
        text = '&é<script>'
        with app.test_request_context('/'):
            unsafe = render_template_string('{{ text|mdstrip }}', text=text)
            safe = render_template_string('{{ text|mdstrip|safe }}', text=text)

        assert unsafe.strip() == '&amp;é&lt;script&gt;'
        assert safe.strip() == '&é<script>'

    def test_mdstrip_custom_end(self, app):
        '''mdstrip should allow a custom ending string'''
        text = '1234567890'
        template = '{{ text|mdstrip(5, "$") }}'
        with app.test_request_context('/'):
            result = render_template_string(template, text=text)

        assert result.strip() == '1234$'


class HtmlToMarkdownTest:
    def test_string_is_untouched(self):
        assert parse_html('foo') == 'foo'

    def test_empty_string_is_untouched(self):
        assert parse_html('') == ''

    def test_none_is_empty_string(self):
        assert parse_html(None) == ''

    def test_parse_basic_html(self):
        text = faker.paragraph()
        html = '<div>{0}</div>'.format(text)

        assert parse_html(html) == text

    def test_content_is_stripped(self):
        text = faker.paragraph()
        spacer = '\n  ' * 3
        assert parse_html(spacer + text + spacer) == text

    def test_parse_html_anchors(self):
        html = '<a href="http://somewhere.com">title</a>'
        assert parse_html(html) == '[title](http://somewhere.com)'

    def test_parse_html_anchors_with_link_title(self):
        url = 'http://somewhere.com/some/path'
        html = '<a href="{0}">{0}</a>'.format(url)
        assert parse_html(html) == '<{0}>'.format(url)

    def test_parse_html_anchors_with_attribute(self):
        url = 'http://somewhere.com/some/path'
        html = '<a href="{0}" target="_blank" title="a title">title</a>'
        expected = '[title]({0} "a title")'

        assert parse_html(html.format(url)) == expected.format(url)
