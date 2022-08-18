import logging

from flask_apispec import use_kwargs, marshal_with

from udata.app import csrf
from udata.api import apiv2_blueprint as apiv2, UDataApiV2
from udata.api.parsers import ModelApiV2Parser
from .models import User
from .apiv2_schemas import user_pagination_schema, UserSchema
from .forms import UserProfileAdminForm


DEFAULT_SORTING = '-created_at'


log = logging.getLogger(__name__)


class UserApiParser(ModelApiV2Parser):
    sorts = {
        'last_name': 'last_name',
        'first_name': 'first_name',
        'datasets': 'metrics.datasets',
        'reuses': 'metrics.reuses',
        'followers': 'metrics.followers',
        'views': 'metrics.views',
        'created': 'created_at',
    }


user_parser_args = UserApiParser.as_request_parser()


@apiv2.route('/users/', endpoint='list_users', methods=['GET'])
@use_kwargs(user_parser_args, location="query")
@marshal_with(user_pagination_schema())
def get_users_list(**kwargs):
    '''List all users'''
    users = User.objects(deleted=None)
    if kwargs.get('q'):
        search_users = users.search_text(kwargs['q'])
        if kwargs.get('sort'):
            return search_users.order_by(kwargs['sort']).paginate(kwargs['page'], kwargs['page_size'])
        else:
            return search_users.order_by('$text_score').paginate(kwargs['page'], kwargs['page_size'])
    if kwargs.get('sort'):
        return users.order_by(kwargs['sort']).paginate(kwargs['page'], kwargs['page_size'])
    return users.order_by(DEFAULT_SORTING).paginate(kwargs['page'], kwargs['page_size'])


@apiv2.route('/users/', endpoint='post_user', methods=['POST'])
@csrf.exempt
@UDataApiV2.secure
@marshal_with(UserSchema())
def post_new_user():
    '''Create a new object'''
    form = UDataApiV2.validate(UserProfileAdminForm)
    user = form.save()
    return user, 201
