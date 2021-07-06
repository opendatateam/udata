from udata.api import api, fields, base_reference

from udata.core.badges.api import badge_fields
from udata.core.dataset.api_fields import dataset_fields
from udata.core.organization.api_fields import org_ref_fields
from udata.core.user.api_fields import user_ref_fields

from .models import REUSE_TYPES, IMAGE_SIZES

BIGGEST_IMAGE_SIZE = IMAGE_SIZES[0]


reuse_fields = api.model('Reuse', {
    'id': fields.String(description='The reuse identifier', readonly=True),
    'title': fields.String(description='The reuse title', required=True),
    'slug': fields.String(
        description='The reuse permalink string', readonly=True),
    'type': fields.String(
        description='The reuse type', required=True, enum=list(REUSE_TYPES)),
    'url': fields.String(
        description='The reuse remote URL (website)', required=True),
    'description': fields.Markdown(
        description='The reuse description in Markdown', required=True),
    'tags': fields.List(
        fields.String, description='Some keywords to help in search'),
    'badges': fields.List(fields.Nested(badge_fields),
                          description='The reuse badges',
                          readonly=True),
    'featured': fields.Boolean(
        description='Is the reuse featured', readonly=True),
    'private': fields.Boolean(
        description='Is the reuse private to the owner or the organization'),
    'image': fields.ImageField(description='The reuse thumbnail thumbnail (cropped) URL'),
    'image_thumbnail': fields.ImageField(attribute='image', size=BIGGEST_IMAGE_SIZE,
        description='The reuse thumbnail thumbnail URL. This is the square '
        '({0}x{0}) and cropped version.'.format(BIGGEST_IMAGE_SIZE)),
    'created_at': fields.ISODateTime(
        description='The reuse creation date', readonly=True),
    'last_modified': fields.ISODateTime(
        description='The reuse last modification date', readonly=True),
    'deleted': fields.ISODateTime(
        description='The organization identifier', readonly=True),
    'datasets': fields.List(
        fields.Nested(dataset_fields), description='The reused datasets'),
    'organization': fields.Nested(
        org_ref_fields, allow_null=True,
        description='The publishing organization', readonly=True),
    'owner': fields.Nested(
        user_ref_fields, description='The owner user', readonly=True,
        allow_null=True),
    'metrics': fields.Raw(attribute=lambda o: o.get_metrics(),
        description='The reuse metrics', readonly=True),
    'uri': fields.UrlFor(
        'api.reuse', lambda o: {'reuse': o},
        description='The reuse API URI', readonly=True),
    'page': fields.UrlFor(
        'reuses.show', lambda o: {'reuse': o},
        description='The reuse page URL', readonly=True, fallback_endpoint='api.reuse'),
}, mask='*,datasets{title,uri,page}')

reuse_page_fields = api.model('ReusePage', fields.pager(reuse_fields))

reuse_suggestion_fields = api.model('ReuseSuggestion', {
    'id': fields.String(description='The reuse identifier', readonly=True),
    'title': fields.String(description='The reuse title', readonly=True),
    'slug': fields.String(
        description='The reuse permalink string', readonly=True),
    'image_url': fields.String(description='The reuse thumbnail URL'),
    'page': fields.UrlFor(
        'reuses.show_redirect', lambda o: {'reuse': o['slug']},
        description='The reuse page URL', readonly=True, fallback_endpoint='api.reuse'),
    'score': fields.Float(
        description='The internal match score', readonly=True),
})


reuse_ref_fields = api.inherit('ReuseReference', base_reference, {
    'title': fields.String(description='The reuse title', readonly=True),
    'image': fields.ImageField(description='The reuse thumbnail thumbnail (cropped) URL'),
    'image_thumbnail': fields.ImageField(attribute='image', size=BIGGEST_IMAGE_SIZE,
        description='The reuse thumbnail thumbnail URL. This is the square '
        '({0}x{0}) and cropped version.'.format(BIGGEST_IMAGE_SIZE)),
    'uri': fields.UrlFor(
        'api.reuse', lambda o: {'reuse': o},
        description='The reuse API URI', readonly=True),
    'page': fields.UrlFor(
        'reuses.show', lambda o: {'reuse': o},
        description='The reuse page URL', readonly=True, fallback_endpoint='api.reuse'),
})

reuse_type_fields = api.model('ReuseType', {
    'id': fields.String(description='The reuse type identifier'),
    'label': fields.String(description='The reuse type display name')
})
