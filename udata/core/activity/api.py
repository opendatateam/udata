import logging

from mongoengine.errors import DoesNotExist

from udata.api import api, API, fields
from udata.models import db, Activity

from udata.core.user.api_fields import user_ref_fields
from udata.core.organization.api_fields import org_ref_fields

log = logging.getLogger(__name__)

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
    @api.doc('activity')
    @api.expect(activity_parser)
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

        qs = qs.order_by('-created_at')
        qs = qs.paginate(args['page'], args['page_size'])

        # Filter out DBRefs
        # Always return a result even not complete
        # But log the error (ie. visible in sentry, silent for user)
        # Can happen when someone manually delete an object in DB (ie. without proper purge)
        safe_items = []
        for item in qs.queryset.items:
            try:
                item.related_to
            except DoesNotExist as e:
                log.error(e, exc_info=True)
            else:
                safe_items.append(item)
        qs.queryset.items = safe_items

        return qs
