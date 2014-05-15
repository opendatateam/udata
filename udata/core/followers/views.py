# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for, redirect

from udata.auth import current_user

from udata.i18n import I18nBlueprint
from udata.frontend.views import DetailView

from udata.core.organization.views import OrgView
from udata.core.dataset.views import DatasetView
from udata.core.user.views import UserView

from .models import Follow

blueprint = I18nBlueprint('followers', __name__)


@blueprint.app_template_global()
@blueprint.app_template_filter()
def is_following(obj):
    return current_user.is_authenticated() and Follow.objects.is_following(current_user._get_current_object(), obj)


class UserFollowersView(UserView, DetailView):
    template_name = 'user/followers.html'

    def get_context(self):
        context = super(UserFollowersView, self).get_context()
        context['followers'] = Follow.objects.followers(self.user)
        return context


class UserFollowingView(UserView, DetailView):
    template_name = 'user/following.html'

    def get_context(self):
        context = super(UserFollowingView, self).get_context()
        context['following'] = Follow.objects.following(self.user)
        return context


class OrganizationFollowersView(OrgView, DetailView):
    template_name = 'organization/followers.html'

    def get_context(self):
        context = super(OrganizationFollowersView, self).get_context()
        context['followers'] = Follow.objects(following=self.organization)
        return context


class DatasetFollowersView(DatasetView, DetailView):
    template_name = 'dataset/followers.html'

    def get_context(self):
        context = super(DatasetFollowersView, self).get_context()
        context['followers'] = Follow.objects(following=self.dataset)
        return context


blueprint.add_url_rule(
    '/organizations/<org:org>/followers/',
    view_func=OrganizationFollowersView.as_view(str('organization'))
)

blueprint.add_url_rule(
    '/datasets/<dataset:dataset>/followers/',
    view_func=DatasetFollowersView.as_view(str('dataset'))
)

blueprint.add_url_rule(
    '/u/<user:user>/followers/',
    view_func=UserFollowersView.as_view(str('user'))
)
