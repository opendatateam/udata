import hashlib
import io

import pydenticon

from flask import redirect, send_file, current_app

from udata import theme, entrypoints
from udata.app import cache

ADORABLE_AVATARS_URL = 'https://api.adorable.io/avatars/{size}/{identifier}.png'  # noqa
ROBOHASH_URL = 'https://robohash.org/{identifier}.png?size={size}x{size}&set={skin}&bgset={bg}'  # noqa


# Default values overriden by theme default and local config
DEFAULTS = {
    'AVATAR_PROVIDER': 'internal',
    # Internal provider
    'AVATAR_INTERNAL_SIZE': 7,
    'AVATAR_INTERNAL_FOREGROUND': [
        'rgb(45,79,255)',
        'rgb(254,180,44)',
        'rgb(226,121,234)',
        'rgb(30,179,253)',
        'rgb(232,77,65)',
        'rgb(49,203,115)',
        'rgb(141,69,170)'
    ],
    'AVATAR_INTERNAL_BACKGROUND': 'rgb(224,224,224)',
    'AVATAR_INTERNAL_PADDING': 10,

    # robohash prodiver
    'AVATAR_ROBOHASH_SKIN': 'set1',
    'AVATAR_ROBOHASH_BACKGROUND': 'bg1',
}


def get_config(key):
    '''
    Get an identicon configuration parameter.

    Precedance order is:
        - application config (`udata.cfg`)
        - theme config
        - default
    '''
    key = 'AVATAR_{0}'.format(key.upper())
    local_config = current_app.config.get(key)
    return local_config or getattr(theme.current, key, DEFAULTS[key])


def get_internal_config(key):
    return get_config('internal_{0}'.format(key))


def get_provider():
    '''Get the current provider from config'''
    name = get_config('provider')
    available = entrypoints.get_all('udata.avatars')
    if name not in available:
        raise ValueError('Unknown avatar provider: {0}'.format(name))
    return available[name]


def get_identicon(identifier, size):
    '''
    Get an identicon for a given identifier at a given size.

    Automatically select the provider from `AVATAR_PROVIDER`

    :returns: a HTTP response, either an image or a redirect
    '''
    return get_provider()(identifier, size)


@cache.memoize()
def generate_pydenticon(identifier, size):
    '''
    Use pydenticon to generate an identicon image.
    All parameters are extracted from configuration.
    '''
    blocks_size = get_internal_config('size')
    foreground = get_internal_config('foreground')
    background = get_internal_config('background')
    generator = pydenticon.Generator(blocks_size, blocks_size,
                                     digest=hashlib.sha1,
                                     foreground=foreground,
                                     background=background)

    # Pydenticon adds padding to the size and as a consequence
    # we need to compute the size without the padding
    padding = int(round(get_internal_config('padding') * size / 100.))
    size = size - 2 * padding
    padding = (padding, ) * 4
    return generator.generate(identifier, size, size,
                              padding=padding,
                              output_format='png')


def internal(identifier, size):
    '''
    Internal provider

    Use pydenticon to generate an identicon.
    '''
    identicon = generate_pydenticon(identifier, size)
    response = send_file(io.BytesIO(identicon), mimetype='image/png')
    etag = hashlib.sha1(identicon).hexdigest()
    response.set_etag(etag)
    return response


def adorable(identifier, size):
    '''
    Adorable Avatars provider

    Simply redirect to the external API.

    See: http://avatars.adorable.io/
    '''
    url = ADORABLE_AVATARS_URL.format(identifier=identifier, size=size)
    return redirect(url)


def robohash(identifier, size):
    '''
    Robohash provider

    Redirect to the Robohash API
    with parameters extracted from configuration.

    See: https://robohash.org/
    '''
    skin = get_config('robohash_skin')
    background = get_config('robohash_background')
    url = ROBOHASH_URL.format(
        identifier=identifier, size=size, skin=skin, bg=background
    )
    return redirect(url)
