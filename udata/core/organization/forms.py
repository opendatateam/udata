# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.auth import current_user
from udata.forms import Form, ModelForm, fields, validators
from udata.i18n import lazy_gettext as _

from .models import (
    OrganizationBadge, Organization, MembershipRequest, Member,
    ORG_BADGE_KINDS, LOGO_SIZES, ORG_ROLES
)

__all__ = (
    'BadgeForm',
    'OrganizationForm',
    'MemberForm',
    'MembershipRequestForm',
    'MembershipRefuseForm',
)


class OrganizationForm(ModelForm):
    model_class = Organization

    name = fields.StringField(_('Name'), [validators.required()])
    acronym = fields.StringField(
        _('Acronym'), description=_('Shorter organization name'))
    description = fields.MarkdownField(
        _('Description'), [validators.required()],
        description=_('The details about your organization'))
    url = fields.URLField(
        _('Website'), description=_('The organization website URL'))
    logo = fields.ImageField(_('Logo'), sizes=LOGO_SIZES)

    def save(self, commit=True, **kwargs):
        '''Register the current user as admin on creation'''
        org = super(OrganizationForm, self).save(commit=False, **kwargs)

        if not org.id:
            user = current_user._get_current_object()
            member = Member(user=user, role='admin')
            org.members.append(member)

        if commit:
            org.save()

        return org


class BadgeForm(ModelForm):
    model_class = OrganizationBadge

    kind = fields.RadioField(
        _('Kind'), [validators.required()],
        choices=ORG_BADGE_KINDS.items(),
        description=_('Kind of badge (public-service, etc)'))


class MembershipRequestForm(ModelForm):
    model_class = MembershipRequest

    user = fields.CurrentUserField()
    comment = fields.StringField(_('Comment'), [validators.required()])


class MembershipRefuseForm(Form):
    comment = fields.StringField(_('Comment'), [validators.required()])


class MemberForm(ModelForm):
    model_class = Member

    role = fields.SelectField(
        _('Role'), default='editor', choices=ORG_ROLES.items(),
        validators=[validators.required()])
