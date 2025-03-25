import re

from flask import current_app, url_for
from netaddr import AddrFormatError, IPAddress
from werkzeug.routing import BuildError

from udata.i18n import _
from udata.settings import Defaults

URL_REGEX = re.compile(
    r"^"
    # scheme
    r"^(?:(?P<scheme>[a-z0-9\.\-]*):)?//"
    # user:pass authentication
    r"(?P<credentials>\S+(?::\S*)?@)?"
    r"(?:"
    # localhost
    r"(?P<localhost>localhost(?:\.localdomain)?)"
    r"|"
    # IPv4 addresses
    r"(?P<ipv4>(?:\d{,3}\.){3}(?:\d{,3}))"
    r"|"
    # IPv6 address
    r"(?:\[(?P<ipv6>[0-9a-f:]+)\])"
    r"|"
    # host name
    r"(?:(?:[a-z\u00a1-\uffff0-9_]-?)*[a-z\u00a1-\uffff0-9]+)"
    # domain name
    r"(?:\.(?:[a-z\u00a1-\uffff0-9_]-?)*[a-z\u00a1-\uffff0-9]+)*"
    # TLD identifier
    r"(?:\.(?P<tld>[a-z0-9\u00a1-\uffff]{2,}))"
    r")"
    # port number
    r"(?::\d{2,5})?"
    # resource path
    r"(?:/\S*)?"
    # query string
    r"(?:\?\S*)?"
    r"$",
    re.UNICODE | re.IGNORECASE,
)


class ValidationError(ValueError):
    """Raised when URL is invalid"""

    pass


def error(url, reason=None):
    __tracebackhide__ = True
    if reason is not None:
        msg = _('Invalid URL "{url}": {reason}').format(url=url, reason=reason)
    else:
        msg = _('Invalid URL "{url}"').format(url=url)

    raise ValidationError(msg)


def config_for(value, key):
    if value is not None:
        return value
    try:
        return current_app.config[key]
    except RuntimeError:
        return getattr(Defaults, key)


def endpoint_for(endpoint, fallback_endpoint=None, **values):
    try:
        return url_for(endpoint, **values)
    except BuildError:
        if fallback_endpoint:
            return url_for(fallback_endpoint, **values)
        return None


def idna(string):
    return string.encode("idna").decode("utf8")


def validate(url, schemes=None, tlds=None, private=None, local=None, credentials=None):
    """
    Validate and normalize an URL

    :param str url: The URL to validate and normalize
    :return str: The normalized URL
    :raises ValidationError: when URL does not validate
    """
    url = url.strip()

    private = config_for(private, "URLS_ALLOW_PRIVATE")
    local = config_for(local, "URLS_ALLOW_LOCAL")
    credentials = config_for(credentials, "URLS_ALLOW_CREDENTIALS")
    schemes = config_for(schemes, "URLS_ALLOWED_SCHEMES")
    tlds = config_for(tlds, "URLS_ALLOWED_TLDS")

    match = URL_REGEX.match(url)
    if not match:
        error(url)

    scheme = (match.group("scheme") or "").lower()
    if scheme and scheme not in schemes:
        error(url, _("Invalid scheme {0}, allowed schemes: {1}").format(scheme, ", ".join(schemes)))

    if not credentials and match.group("credentials"):
        error(url, _("Credentials in URL are not allowed"))

    tld = match.group("tld")
    if tld and tld not in tlds and idna(tld) not in tlds:
        error(url, _("Invalid TLD {0}").format(tld))

    ip = match.group("ipv6") or match.group("ipv4")
    if ip:
        try:
            ip = IPAddress(ip)
        except AddrFormatError:
            error(url)
        if ip.is_multicast():
            error(url, _("{0} is a multicast IP").format(ip))
        elif not ip.is_loopback() and ip.is_hostmask() or ip.is_netmask():
            error(url, _("{0} is a mask IP").format(ip))

    if not local:
        if ip and ip.is_loopback() or match.group("localhost"):
            error(url, _("is a local URL"))

    if (
        not private
        and ip
        and (ip.is_link_local() or ip.is_ipv4_private_use() or ip.is_ipv6_unique_local())
    ):
        error(url, _("is a private URL"))

    return url
