from mongoengine.fields import StringField

from udata import uris


class URLField(StringField):
    '''
    An URL field using the udata URL normalization and validation rules.

    The URL spaces are automatically stripped.

    Non-specified parameters fallback app level settings,
    ie. ``URLS_ALLOW_PRIVATE``, ``URLS_ALLOW_LOCAL``
    ``URLS_ALLOWED_SCHEMES`` and ``URLS_ALLOWED_TLDS``

    :params bool private: Allow private URLs
    :params bool local: Allow local URLs
    :params list schemes: List of allowed schemes
    :params list tlds: List of allowed TLDs

    '''
    def __init__(self, private=None, local=None, schemes=None, tlds=None,
                 **kwargs):
        super(URLField, self).__init__(**kwargs)
        self.private = private
        self.local = local
        self.schemes = schemes
        self.tlds = tlds

    def to_python(self, value):
        value = super(URLField, self).to_python(value)
        if value:
            return value.strip()

    def validate(self, value):
        super(URLField, self).validate(value)
        kwargs = {
            a: getattr(self, a)
            for a in ('private', 'local', 'schemes', 'tlds')
            if getattr(self, a) is not None
        }
        try:
            uris.validate(value, **kwargs)
        except uris.ValidationError as e:
            self.error(str(e))
