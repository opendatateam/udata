import mock
import os

from io import BytesIO

from PIL import Image

from udata.mail import mail_sent

from contextlib import contextmanager
from datetime import timedelta
from urllib.parse import urljoin, urlparse, parse_qs

from flask import request, url_for, json


def assert_equal_dates(datetime1, datetime2, limit=1):  # Seconds.
    """Lax date comparison, avoid comparing milliseconds and seconds."""
    __tracebackhide__ = True
    delta = (datetime1 - datetime2)
    assert timedelta(seconds=-limit) <= delta <= timedelta(seconds=limit)


def assert_starts_with(haystack, needle):
    __tracebackhide__ = True
    msg = '{haystack} does not start with {needle}'.format(
        haystack=haystack, needle=needle
    )
    assert haystack.startswith(needle), msg


def assert_json_equal(first, second):
    '''Ensure two dict produce the same JSON'''
    __tracebackhide__ = True
    json1 = json.loads(json.dumps(first))
    json2 = json.loads(json.dumps(second))
    assert json1 == json2


@contextmanager
def mock_signals(callback, *signals):
    __tracebackhide__ = True
    specs = []

    def handler(sender, **kwargs):
        pass

    for signal in signals:
        m = mock.Mock(spec=handler)
        signal.connect(m, weak=False)
        specs.append((signal, m))

    yield

    for signal, mock_handler in specs:
        signal.disconnect(mock_handler)
        signal_name = getattr(signal, 'name', str(signal))
        callback(signal_name, mock_handler)


@contextmanager
def assert_emit(*signals):
    __tracebackhide__ = True
    msg = 'Signal "{0}" should have been emitted'

    def callback(name, handler):
        assert handler.called, msg.format(name)

    with mock_signals(callback, *signals):
        yield


@contextmanager
def assert_not_emit(*signals):
    __tracebackhide__ = True
    msg = 'Signal "{0}" should NOT have been emitted'

    def callback(name, handler):
        assert not handler.called, msg.format(name)

    with mock_signals(callback, *signals):
        yield


@contextmanager
def capture_mails():
    mails = []

    def on_mail_sent(mail):
        mails.append(mail)

    mail_sent.connect(on_mail_sent)

    yield mails

    mail_sent.disconnect(on_mail_sent)


REDIRECT_CODES = (301, 302, 303, 305, 307, 308)
REDIRECT_MSG = 'HTTP Status {} expected but got {{}}'.format(
    ', '.join(str(code) for code in REDIRECT_CODES)
)


def assert_redirects(response, location, message=None):
    """
    Checks if response is an HTTP redirect to the
    given location.
    :param response: Flask response
    :param location: relative URL path to SERVER_NAME or an absolute URL
    :param message: an optional failure message
    """
    __tracebackhide__ = True
    parts = urlparse(location)

    if parts.netloc:
        expected_location = location
    else:
        expected_location = urljoin('http://local.test', location)
    not_redirect = REDIRECT_MSG.format(response.status_code)
    assert response.status_code in REDIRECT_CODES, message or not_redirect
    assert response.location == expected_location, message


def assert_status(response, status_code, message=None):
    """
    Helper method to check matching response status.

    Extracted from parent class to improve output in case of JSON.

    :param response: Flask response
    :param status_code: response status code (e.g. 200)
    :param message: Message to display on test failure
    """
    __tracebackhide__ = True

    message = message or 'HTTP Status %s expected but got %s' \
                         % (status_code, response.status_code)
    if response.mimetype == 'application/json':
        try:
            second_line = 'Response content is {0}'.format(response.json)
            message = '\n'.join((message, second_line))
        except Exception:
            pass
    assert response.status_code == status_code, message


def assert200(response):
    __tracebackhide__ = True
    assert_status(response, 200)


def assert201(response):
    __tracebackhide__ = True
    assert_status(response, 201)


def assert204(response):
    __tracebackhide__ = True
    assert_status(response, 204)


def assert400(response):
    __tracebackhide__ = True
    assert_status(response, 400)


def assert401(response):
    __tracebackhide__ = True
    assert_status(response, 401)


def assert403(response):
    __tracebackhide__ = True
    assert_status(response, 403)


def assert404(response):
    __tracebackhide__ = True
    assert_status(response, 404)


def assert410(response):
    __tracebackhide__ = True
    assert_status(response, 410)


def assert500(response):
    __tracebackhide__ = True
    assert_status(response, 500)


def full_url(*args, **kwargs):
    '''Build a full URL'''
    return urljoin(request.url_root, url_for(*args, **kwargs))


def data_path(filename):
    '''Get a test data path'''
    return os.path.join(os.path.dirname(__file__), 'data', filename)


def assert_command_ok(result):
    __tracebackhide__ = True
    msg = 'Command failed with exit code {0.exit_code} and output:\n{0.output}'
    assert result.exit_code == 0, msg.format(result)


def assert_urls_equal(url1, url2):
    __tracebackhide__ = True
    p1 = urlparse(url1)
    p2 = urlparse(url2)
    assert p1.scheme == p2.scheme, 'Scheme does not match'
    assert p1.netloc == p2.netloc, 'Network location does not match'
    assert p1.path == p2.path, 'Path does not match'
    q1 = parse_qs(p1.query)
    q2 = parse_qs(p2.query)
    assert q1 == q2, 'Query does not match'
    assert p1.fragment == p2.fragment, 'Fragment does not match'


def assert_cors(response):
    '''CORS headers presence assertion'''
    __tracebackhide__ = True
    assert 'Access-Control-Allow-Origin' in response.headers


def create_test_image():
    file = BytesIO()
    image = Image.new('RGBA', size=(50, 50), color=(155, 0, 0))
    image.save(file, 'png')
    file.name = 'test.png'
    file.seek(0)
    return file
