from flask import current_app, url_for
from flask_cdn import url_for as cdn_url_for


def cdn_for(endpoint, **kwargs):
    '''
    Get a CDN URL for a static assets.

    Do not use a replacement for all flask.url_for calls
    as it is only meant for CDN assets URLS.
    (There is some extra round trip which cost is justified
    by the CDN assets prformance improvements)
    '''
    if current_app.config['CDN_DOMAIN']:
        if not current_app.config.get('CDN_DEBUG'):
            kwargs.pop('_external', None)  # Avoid the _external parameter in URL
        return cdn_url_for(endpoint, **kwargs)
    return url_for(endpoint, **kwargs)
