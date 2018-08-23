# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from udata import uris
from udata.settings import Defaults


PUBLIC_HOSTS = [
    'http://foo.com/blah_blah',
    'http://foo.com/blah_blah/',
    'http://foo.com/blah_blah_(wikipedia)',
    'http://foo.com/blah_blah_(wikipedia)_(again)',
    'http://www.example.com/wpstyle/?p=364',
    'https://www.example.com/foo/?bar=baz&inga=42&quux',
    'http://✪df.ws/123',
    'http://➡.ws/䨹',
    'http://⌘.ws',
    'http://⌘.ws/',
    'http://foo.com/blah_(wikipedia)#cite-1',
    'http://foo.com/blah_(wikipedia)_blah#cite-1',
    'http://foo.com/unicode_(✪)_in_parens',
    'http://foo.com/(something)?after=parens',
    'http://☺.damowmow.com/',
    'http://code.google.com/events/#&product=browser',
    'http://j.mp',
    'ftp://foo.bar/baz',
    'http://foo.bar/?q=Test%20URL-encoded%20stuff',
    'http://مثال.إختبار.com',
    'http://例子.测试.com',
    'http://उदाहरण.परीक्षा.com',
    'http://-.~_!$&\'()*+,;=:%40:80%2f::::::@example.com',
    'http://1337.net',
    'http://a.b-c.de',
    'https://foo_bar.example.com/',
    'ftps://foo.bar/',
    '//foo.bar/',
]

PUBLIC_HOSTS_IDN = [
    'http://例子.中国',
    'http://somewhere.укр',
]

WITH_CREDENTIALS = [
    'http://userid:password@example.com:8080',
    'http://userid:password@example.com:8080/',
    'http://userid@example.com',
    'http://userid@example.com/',
    'http://userid@example.com:8080',
    'http://userid@example.com:8080/',
    'http://userid:password@example.com',
    'http://userid:password@example.com/',
]

PUBLIC_IPS = [
    'http://142.42.1.1/',
    'http://142.42.1.1:8080',
    'http://142.42.1.1:8080/',
    'http://223.255.255.254',
    'http://[2a00:1450:4007:80e::2004]',
    'http://[2a00:1450:4007:80e::2004]:8080',
    'http://[2a00:1450:4007:80e::2004]:8080/',
]

PUBLIC = PUBLIC_HOSTS + PUBLIC_HOSTS_IDN + PUBLIC_IPS + WITH_CREDENTIALS

PRIVATE_IPS = [
    'http://10.1.1.1',
    'http://10.1.1.1:8080',
    'http://10.1.1.1:8080/index.html',
    'http://10.1.1.254',
    'http://10.1.1.254:8080',
    'http://10.1.1.254:8080/index.html',
    'http://[fc00::1]',
    'http://[fc00::1]:8080',
    'http://[fc00::1]:8080/index.html',
]

PRIVATE = PRIVATE_IPS

LOCAL_HOSTS = [
    'http://localhost',
    'http://localhost:8080',
    'http://localhost:8080/index.html',
    'http://localhost.localdomain',
    'http://localhost.localdomain:8080',
    'http://localhost.localdomain:8080/index.html',
]

LOCAL_IPS = [
    'http://127.0.0.1',
    'http://127.0.0.1:8080',
    'http://127.0.0.1:8080/index.html',
    'http://127.0.1.1',
    'http://127.0.1.1:8080',
    'http://127.0.1.1:8080/index.html',
    'http://[::1]',
    'http://[::1]:8080',
    'http://[::1]:8080/index.html',
]

LOCAL = LOCAL_HOSTS + LOCAL_IPS

MULTICAST = [
    'http://224.1.1.1',
    'http://224.1.1.1:8080',
    'http://224.1.1.1:8080/index.html',
    'http://[ff00::1]',
    'http://[ff00::1]:8080',
    'http://[ff00::1]:8080/index.html',
]

INVALID = [
    'http://',
    'h/://.',
    'http://..',
    'http://../',
    'http://?',
    'http://??',
    'http://??/',
    'http://#',
    'http://##',
    'http://##/',
    'http://foo.bar?q=Spaces should be encoded',
    'http://foo.bar?q=Spaces should be encoded with unicode é',
    '//',
    '//a',
    '///a',
    '///',
    'http:///a',
    'foo.com',
    'rdar://1234',
    'h://test',
    'http:// shouldfail.com',
    ':// should fail',
    'http://foo.bar/foo(bar)baz quux',
    'http://-error-.invalid/',
    'http://_error_.invalid/',
    'http://a.b--c.de/',
    'http://-a.b.co',
    'http://a.b-.co',
    'http://0.0.0.0',
    'http://10.1.1.0',
    'http://10.1.1.255',
    'http://1.1.1.1.1',
    'http://123.123.123',
    'http://3628126748',
    'http://.www.foo.bar/',
    'http://www.foo.bar./',
    'http://.www.foo.bar./',
    'http://[fffff:1450:4007:80e::2004]',
    'http://[fffff:1450:4007:80e::2004]:8080',
    'http://[fffff:1450:4007:80e::2004]:8080/index.html',
    'http://[::]',
    'http://[::]:8080',
    'http://[::]:8080/index.html',
]

DEFAULT_SCHEMES = Defaults.URLS_ALLOWED_SCHEMES
# Custom schemes not in uris.SCHEMES
CUSTOM_SCHEMES = ['irc', 'unknown']

# Extract some default TLDs
DEFAULT_TLDS = list(Defaults.URLS_ALLOWED_TLDS)[:2]
# Custom TLDs not in IANA official list
CUSTOM_TLDS = ['i2', 'unknown']


def test_validate_strip_url():
    assert uris.validate('  http://somewhere.com  ') == 'http://somewhere.com'


@pytest.mark.parametrize('url', PUBLIC_HOSTS)
def test_default_should_validate_public_urls(url):
    assert uris.validate(url) == url


@pytest.mark.parametrize('url', PUBLIC_HOSTS_IDN)
def test_default_should_validate_public_urls_with_utf8_tld(url):
    assert uris.validate(url) == url


@pytest.mark.parametrize('url', PUBLIC_IPS)
def test_default_should_validate_public_ips(url):
    assert uris.validate(url) == url


@pytest.mark.parametrize('scheme', DEFAULT_SCHEMES)
def test_default_should_validate_default_schemes(scheme):
    url = '{0}://somewhere.com'.format(scheme)
    assert uris.validate(url) == url


@pytest.mark.parametrize('scheme', CUSTOM_SCHEMES)
def test_default_should_not_validate_non_default_schemes(scheme):
    url = '{0}://somewhere.com'.format(scheme)
    with pytest.raises(uris.ValidationError):
        uris.validate(url)


@pytest.mark.parametrize('tld', CUSTOM_TLDS)
def test_default_should_not_validate_unknown_tlds(tld):
    url = 'http://somewhere.{0}'.format(tld)
    with pytest.raises(uris.ValidationError):
        uris.validate(url)


@pytest.mark.parametrize('url', PRIVATE)
def test_default_should_not_validate_private_urls(url):
    with pytest.raises(uris.ValidationError):
        uris.validate(url)


@pytest.mark.parametrize('url', LOCAL_HOSTS)
def test_default_should_not_validate_local_hosts(url):
    with pytest.raises(uris.ValidationError):
        uris.validate(url)


@pytest.mark.parametrize('url', INVALID)
def test_should_not_validate_bad_urls(url):
    with pytest.raises(uris.ValidationError):
        uris.validate(url)


@pytest.mark.parametrize('url', MULTICAST)
def test_should_not_validate_multicast_urls(url):
    with pytest.raises(uris.ValidationError):
        uris.validate(url)


@pytest.mark.parametrize('url', PUBLIC + PRIVATE)
def test_private_should_validate_public_and_private_urls(url):
    assert uris.validate(url, private=True) == url


@pytest.mark.parametrize('url', LOCAL)
def test_private_should_not_validate_local_urls(url):
    with pytest.raises(uris.ValidationError):
        uris.validate(url, private=True)


@pytest.mark.parametrize('url', PUBLIC + LOCAL)
def test_local_should_validate_public_and_local_urls(url):
    assert uris.validate(url, local=True) == url


@pytest.mark.parametrize('url', PRIVATE)
def test_local_should_not_validate_private_urls(url):
    with pytest.raises(uris.ValidationError):
        uris.validate(url, local=True)


@pytest.mark.parametrize('url', PUBLIC + LOCAL + PRIVATE)
def test_private_local_should_validate_any_valid_urls(url):
    assert uris.validate(url, local=True, private=True) == url


@pytest.mark.parametrize('scheme', CUSTOM_SCHEMES)
def test_custom_schemes(scheme):
    url = '{0}://somewhere.com'.format(scheme)
    assert uris.validate(url, schemes=CUSTOM_SCHEMES) == url


@pytest.mark.parametrize('scheme', DEFAULT_SCHEMES)
def test_custom_schemes_should_not_validate_defaults(scheme):
    url = '{0}://somewhere.com'.format(scheme)
    with pytest.raises(uris.ValidationError):
        uris.validate(url, schemes=CUSTOM_SCHEMES)


@pytest.mark.parametrize('tld', CUSTOM_TLDS)
def test_custom_tlds(tld):
    url = 'http://somewhere.{0}'.format(tld)
    assert uris.validate(url, tlds=CUSTOM_TLDS) == url


@pytest.mark.parametrize('tld', DEFAULT_TLDS)
def test_custom_tlds_should_not_validate_defaults(tld):
    url = 'http://somewhere.{0}'.format(tld)
    with pytest.raises(uris.ValidationError):
        uris.validate(url, tlds=CUSTOM_TLDS)


@pytest.mark.parametrize('url', WITH_CREDENTIALS)
def test_with_credentials(url):
    assert uris.validate(url) == url


@pytest.mark.parametrize('url', WITH_CREDENTIALS)
def test_with_credentials_disabled(url):
    with pytest.raises(uris.ValidationError):
        uris.validate(url, credentials=False)

