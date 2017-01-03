# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.api import api, API, fields
from udata.models import db, Activity

from udata.core.user.api_fields import user_ref_fields
from udata.core.organization.api_fields import org_ref_fields


activity_fields = api.model('Activity', {
    'actor': fields.Nested(
        user_ref_fields,
        description='The user who performed the action', readonly=True),
    'organization': fields.Nested(
        org_ref_fields, allow_null=True, readonly=True,
        description='The organization who performed the action'),
    'related_to': fields.String(
        attribute='related_to',
        description='The activity target name', required=True),
    'related_to_id': fields.String(
        attribute='related_to.id',
        description='The activity target object identifier', required=True),
    'related_to_kind': fields.String(
        attribute='related_to.__class__.__name__',
        description='The activity target object class name', required=True),
    'related_to_url': fields.String(
        attribute='related_to.display_url',
        description='The activity target model', required=True),
    'created_at': fields.ISODateTime(
        description='When the action has been performed', readonly=True),
    'label': fields.String(
        description='The label of the activity', required=True),
    'key': fields.String(
        description='The key of the activity', required=True),
    'icon': fields.String(
        description='The icon of the activity', required=True),
    'kwargs': fields.Raw(description='Some action specific context'),
})

activity_page_fields = api.model('ActivityPage', fields.pager(activity_fields))

activity_parser = api.page_parser()
activity_parser.add_argument(
    'user', type=str, help='Filter activities for that particular user',
    location='args')
activity_parser.add_argument(
    'organization', type=str,
    help='Filter activities for that particular organization',
    location='args')


@api.route('/activity', endpoint='activity')
class SiteActivityAPI(API):
    @api.doc('activity', parser=activity_parser)
    @api.marshal_list_with(activity_page_fields)
    def get(self):
        '''Fetch site activity, optionally filtered by user of org.'''
        args = activity_parser.parse_args()
        qs = Activity.objects

        if args['organization']:
            qs = qs(db.Q(organization=args['organization']) |
                    db.Q(related_to=args['organization']))

        if args['user']:
            qs = qs(actor=args['user'])

        return (qs.order_by('-created_at')
                  .paginate(args['page'], args['page_size']))
