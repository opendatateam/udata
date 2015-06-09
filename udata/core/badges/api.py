# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask.ext.security import current_user

from udata.api import api, API, fields
from udata.models import Dataset, DatasetBadge, Organization, OrganizationBadge
from udata.core.user.api_fields import user_ref_fields

from .forms import BadgeCreateForm
from .models import Badge
from .permissions import BadgePermission
from .signals import on_badge_added, on_badge_removed

ns = api.namespace('badges', 'Badge related operations')


badge_fields = api.model('Badge', {
    'id': fields.String(description='The badge identifier', readonly=True),
    'subject': fields.String(attribute='subject.id', description='The badge target object identifier', required=True),
    'kind': fields.String(description='The badge kind', required=True),
    'created': fields.ISODateTime(description='The badge creation date', readonly=True),
    'created_by': fields.Nested(user_ref_fields, description='The user who set the badge', required=True),
    'removed': fields.ISODateTime(description='The badge unset date', readonly=True),
    'removed_by': fields.Nested(user_ref_fields, description='The user who unset the badge', required=True, allow_null=True),
    'url': fields.UrlFor('api.badge', description='The badge API URI', readonly=True),
})

badge_page_fields = api.model('BadgePage', fields.pager(badge_fields))


parser = api.parser()
parser.add_argument('for', type=str, location='args', action='append', help='Filter badges for a given subject')
parser.add_argument('removed', type=bool, default=False, location='args', help='Filter removed badges')
parser.add_argument('kind', type=str, location='args', action='append', help='Filter badges for a given kind')
parser.add_argument('page', type=int, default=1, location='args', help='The page to fetch')
parser.add_argument('page_size', type=int, default=20, location='args', help='The page size to fetch')


@ns.route('/<id>/', endpoint='badge')
@api.doc(model=badge_fields)
class BadgeAPI(API):
    '''
    Base class for a badge.
    '''
    @api.doc('get_badge')
    @api.marshal_with(badge_fields)
    def get(self, id):
        '''Get a badge given its ID'''
        badge = Badge.objects.get_or_404(id=id)
        return badge

    @api.secure
    @api.doc('remove_badge')
    @api.expect(badge_fields)
    @api.response(403, 'Not allowed to remove this badge')
    def delete(self, id):
        '''Remove a badge given its ID'''
        badge = Badge.objects.get_or_404(id=id)
        BadgePermission(badge).test()
        badge.removed_by = current_user._get_current_object()
        badge.removed = datetime.now()
        badge.save()
        on_badge_removed.send(badge)
        return '', 204


@ns.route('/', endpoint='badges')
class BadgesAPI(API):
    '''
    Base class for a list of badges.
    '''
    @api.doc('list_badges')
    @api.marshal_with(badge_page_fields)
    @api.doc(parser=parser)
    def get(self):
        '''List all Badges'''
        args = parser.parse_args()
        badges = Badge.objects
        if args['for']:
            badges = badges(subject__in=args['for'])
        if args['kind']:
            badges = badges(kind=args['kind'])
        if not args['removed']:
            badges = badges(removed=None)
        return badges.paginate(args['page'], args['page_size'])

    @api.secure
    @api.expect(badge_fields)
    @api.doc('create_badge')
    @api.marshal_with(badge_fields)
    def post(self):
        '''Create a new Badge'''
        form = api.validate(BadgeCreateForm)
        if isinstance(form.subject.data, Dataset):
            model = DatasetBadge
        elif isinstance(form.subject.data, Organization):
            model = OrganizationBadge
        badge = model.objects.create(
            created_by=current_user.id,
            subject=form.subject.data.id,
            kind=form.kind.data,
        )
        on_badge_added.send(badge)

        return badge, 201
