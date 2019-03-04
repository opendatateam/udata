# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.auth import current_user
from udata.forms import Form, ModelForm, fields, validators
from udata.i18n import lazy_gettext as _

from .models import (
    Organization, MembershipRequest, Member, LOGO_SIZES, ORG_ROLES
)

__all__ = (
    'OrganizationForm',
    'MemberForm',
    'MembershipRequestForm',
    'MembershipRefuseForm',
)


class OrganizationForm(ModelForm):
    model_class = Organization

    name = fields.StringField(_('Name'), [validators.DataRequired()])
    acronym = fields.StringField(
        _('Acronym'), description=_('Shorter organization name'))
    description = fields.MarkdownField(
        _('Description'), [validators.DataRequired()],
        description=_('The details about your organization'))
    url = fields.URLField(
        _('Website'), description=_('The organization website URL'))
    logo = fields.ImageField(_('Logo'), sizes=LOGO_SIZES)

    deleted = fields.DateTimeField()
    extras = fields.ExtrasField()

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


class MembershipRequestForm(ModelForm):
    model_class = MembershipRequest

    user = fields.CurrentUserField()
    comment = fields.StringField(_('Comment'), [validators.DataRequired()])


class MembershipRefuseForm(Form):
    comment = fields.StringField(_('Comment'), [validators.DataRequired()])


class MemberForm(ModelForm):
    model_class = Member

    role = fields.SelectField(
        _('Role'), default='editor', choices=ORG_ROLES.items(),
        validators=[validators.DataRequired()])
