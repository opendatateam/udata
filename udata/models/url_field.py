# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from mongoengine.fields import URLField as MEURLField


IP_MIDDLE_OCTET = r'(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5]))'
IP_LAST_OCTET = r'(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))'

URL_REGEX = re.compile(
    r'^'
    # scheme is validated separately
    r'^(?:[a-z0-9\.\-]*)://'
    # user:pass authentication
    r'(?:\S+(?::\S*)?@)?'
    r'(?:'
    r'(?P<private_ip>'
    # IP address exclusion
    # private & local networks
    r'(?:localhost)|'
    r'(?:(?:10|127)' + IP_MIDDLE_OCTET + r'{2}' + IP_LAST_OCTET + r')|'
    r'(?:(?:169\.254|192\.168)' + IP_MIDDLE_OCTET + IP_LAST_OCTET + r')|'
    r'(?:172\.(?:1[6-9]|2\d|3[0-1])' + IP_MIDDLE_OCTET + IP_LAST_OCTET + r'))'
    r'|'
    # IP address dotted notation octets
    # excludes loopback network 0.0.0.0
    # excludes reserved space >= 224.0.0.0
    # excludes network & broadcast addresses
    # (first & last IP address of each class)
    r'(?P<public_ip>'
    r'(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])'
    r'' + IP_MIDDLE_OCTET + r'{2}'
    r'' + IP_LAST_OCTET + r')'
    r'|'
    # host name
    r'(?:(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)'
    # domain name
    r'(?:\.(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)*'
    # TLD identifier
    r'(?:\.(?:[a-z\u00a1-\uffff]{2,}))'
    r')'
    # port number
    r'(?::\d{2,5})?'
    # resource path
    r'(?:/\S*)?'
    # query string
    r'(?:\?\S*)?'
    r'$',
    re.UNICODE | re.IGNORECASE
)


class URLField(MEURLField):
    '''
    An URL field that automatically strips extra spaces
    and support uncode domain and paths.

    Public URL can be enforced with `public=True`

    URL_REGEX has been extracted and adapted from:
        https://github.com/kvesteri/validators/blob/master/validators/url.py

    Main changes are:
        - scheme validation is handled separately instead of being hard coded
        - handle `localhost` as a valid private url
    '''
    _URL_REGEX = URL_REGEX

    def __init__(self, public=False, **kwargs):
        super(URLField, self).__init__(**kwargs)
        self.public = public

    def to_python(self, value):
        value = super(URLField, self).to_python(value)
        if value:
            return value.strip()

    def validate(self, value):
        super(URLField, self).validate(value)
        if self.public:
            match = self.url_regex.match(value)
            if match and match.group('private_ip'):
                self.error('Invalid URL: "{0}" is not public URL')
