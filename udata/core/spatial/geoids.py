'''
This module centralize GeoID resources and helpers.

See https://github.com/etalab/geoids for more details
'''


from datetime import date, datetime


__all__ = ('END_OF_TIME', 'GeoIDError', 'parse', 'build', 'from_zone')

# Arbitrary date value used as validity.end
# for zone not yet ended
END_OF_TIME = date(9999, 12, 31)


class GeoIDError(ValueError):
    '''Raised when an error occur while parsing or building a GeoID'''
    pass


def parse(text):
    '''Parse a geoid from text and return a tuple (level, code, validity)'''
    if '@' in text:
        spatial, validity = text.split('@')
    else:
        spatial = text
        validity = 'latest'
    spatial = spatial.lower().replace('/', ':')  # Backward compatibility
    if ':' not in spatial:
        raise GeoIDError('Bad GeoID format: {0}'.format(text))
    # country-subset is a special case:
    if spatial.startswith('country-subset:'):
        level, code = spatial.split(':', 1)
    else:
        level, code = spatial.rsplit(':', 1)
    return level, code, validity


def build(level, code, validity=None):
    '''Serialize a GeoID from its parts'''
    spatial = ':'.join((level, code))
    if not validity:
        return spatial
    elif isinstance(validity, str):
        return '@'.join((spatial, validity))
    elif isinstance(validity, datetime):
        return '@'.join((spatial, validity.date().isoformat()))
    elif isinstance(validity, date):
        return '@'.join((spatial, validity.isoformat()))
    else:
        msg = 'Unknown GeoID validity type: {0}'
        raise GeoIDError(msg.format(type(validity).__name__))


def from_zone(zone):
    '''Build a GeoID from a given zone'''
    validity = zone.validity.start if zone.validity else None
    return build(zone.level, zone.code, validity)
