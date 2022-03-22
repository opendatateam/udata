from jinja2 import contextfilter

from udata_front.frontend import front


@front.app_template_filter()
@contextfilter
def permissions(ctx, resources):
    '''Return permissions for resources'''
    permissions = {}
    for resource in resources:
        element_to_check = resource if resource.from_community else resource.dataset
        can_edit_resource = ctx['can_edit_resource']
        permissions[str(resource.id)] = can_edit_resource(element_to_check).can()
    return permissions


@front.app_template_filter()
def filesize(value):
    '''Display a human readable filesize'''
    suffix = 'o'
    for unit in '', 'K', 'M', 'G', 'T', 'P', 'E', 'Z':
        if abs(value) < 1024.0:
            return "%3.1f%s%s" % (value, unit, suffix)
        value /= 1024.0
    return "%.1f%s%s" % (value, 'Y', suffix)


@front.app_template_global()
def resource_image(resource):
    '''Display a human recognizable image for a resource'''
    formats = {
        'txt': 'documentation',
        'pdf': 'documentation',
        'rtf': 'documentation',
        'odt': 'documentation',
        'doc': 'documentation',
        'docx': 'documentation',
        'epub': 'documentation',
        'json': 'code',
        'sql': 'code',
        'xml': 'code',
        'xsd': 'code',
        'shp': 'code',
        'kml': 'code',
        'kmz': 'code',
        'gpx': 'code',
        'shx': 'code',
        'ovr': 'code',
        'geojson': 'code',
        'gpkg': 'code',
        'grib2': 'code',
        'dbf': 'code',
        'prj': 'code',
        'sqlite': 'code',
        'db': 'code',
        'sbn': 'code',
        'sbx': 'code',
        'cpg': 'code',
        'lyr': 'code',
        'owl': 'code',
        'dxf': 'code',
        'ics': 'code',
        'rdf': 'code',
        'ttl': 'code',
        'n3': 'code',
        'tar': 'archive',
        'gz': 'archive',
        'tgz': 'archive',
        'rar': 'archive',
        'zip': 'archive',
        '7z': 'archive',
        'xz': 'archive',
        'bz2': 'archive',
        'url': 'link',
        'csv': 'table',
        'ods': 'table',
        'xls': 'table',
        'xlsx': 'table',
    }
    return 'svg/resources/{}.svg'.format(formats.get(resource.format, 'file'))
