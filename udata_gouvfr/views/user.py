import logging

from flask import abort, g
from flask_security import current_user

from udata_gouvfr.views.base import DetailView
from udata.models import User, Activity, Organization, Dataset, Reuse, Follow
from udata.i18n import I18nBlueprint

from udata.core.user.permissions import sysadmin


blueprint = I18nBlueprint('users', __name__, url_prefix='/users')

log = logging.getLogger(__name__)


@blueprint.before_app_request
def set_g_sysadmin():
    g.sysadmin = sysadmin


@blueprint.app_context_processor
def inject_sysadmin_perms():
    return {'sysadmin': sysadmin}


class UserView(object):
    model = User
    object_name = 'user'

    @property
    def user(self):
        return self.get_object()

    def get_context(self):
        context = super(UserView, self).get_context()
        context['organizations'] = Organization.objects(
            members__user=self.user)
        return context


@blueprint.route('/<user:user>/datasets/', endpoint='datasets')
class UserDatasetsView(UserView, DetailView):
    template_name = 'user/datasets.html'

    def get_context(self):
        context = super(UserDatasetsView, self).get_context()
        context['datasets'] = Dataset.objects(owner=self.user).visible()
        return context


@blueprint.route('/<user:user>/reuses/', endpoint='reuses')
class UserReusesView(UserView, DetailView):
    template_name = 'user/reuses.html'

    def get_context(self):
        context = super(UserReusesView, self).get_context()
        context['reuses'] = Reuse.objects(owner=self.user).visible()
        return context


@blueprint.route('/<user:user>/', endpoint='show')
class UserActivityView(UserView, DetailView):
    template_name = 'user/activity.html'

    def get_context(self):
        if current_user.is_anonymous or not current_user.sysadmin:
            if not self.user.active:
                abort(410, 'User is not active')
        context = super(UserActivityView, self).get_context()
        context['activities'] = (Activity.objects(actor=self.object)
                                         .order_by('-created_at').limit(15))
        return context


@blueprint.route('/<user:user>/following/', endpoint='following')
class UserFollowingView(UserView, DetailView):
    template_name = 'user/following.html'

    def get_context(self):
        context = super(UserFollowingView, self).get_context()
        datasets, reuses, organizations, users = [], [], [], []

        for follow in Follow.objects.following(self.user).select_related():
            if isinstance(follow.following, Organization):
                organizations.append(follow.following)
            elif isinstance(follow.following, Reuse):
                reuses.append(follow.following)
            elif isinstance(follow.following, Dataset):
                datasets.append(follow.following)
            elif isinstance(follow.following, User):
                users.append(follow.following)
            else:
                log.warning(
                    'Follow object %s has not dereferenced %s',
                    follow.id, follow.following)

        context.update({
            'followed_datasets': sorted(datasets, key=lambda d: d.title),
            'followed_reuses': sorted(reuses, key=lambda r: r.title),
            'followed_organizations': sorted(organizations,
                                             key=lambda o: o.name),
            'followed_users': sorted(users, key=lambda u: u.fullname),
        })

        return context


@blueprint.route('/<user:user>/followers/', endpoint='followers')
class UserFollowersView(UserView, DetailView):
    template_name = 'user/followers.html'

    def get_context(self):
        context = super(UserFollowersView, self).get_context()
        context['followers'] = (Follow.objects.followers(self.user)
                                              .order_by('follower.fullname'))
        return context
