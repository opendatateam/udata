from udata.auth import current_user
from udata.forms import Form, ModelForm, fields, validators
from udata.i18n import lazy_gettext as _

from .models import (
    Organization, MembershipRequest, Member, LOGO_SIZES, ORG_ROLES,
    TITLE_SIZE_LIMIT, DESCRIPTION_SIZE_LIMIT, ORG_BID_SIZE_LIMIT, ORG_BID_FORMAT
)

__all__ = (
    'OrganizationForm',
    'MemberForm',
    'MembershipRequestForm',
    'MembershipRefuseForm',
)


def org_bid_check(form, field):
    if field.data:
        # EID checks are country dependant. Following one is suitable for France.
        if ORG_BID_FORMAT == 'siret':
            siret_number = str(field.data)
            # Length control done here instead of using WTForm validator because field must remain optional.
            if len(siret_number) != 14:
                raise validators.ValidationError(_('A siret number is made of 14 digits'))
            # Siret exception for the french postal service which business number id does not match the algorithm.
            if siret_number == '35600000000048':
                return
            # Checksum verification on only the SIREN part, the 9 first digits.
            try:
                chiffres = [int(chiffre) for chiffre in siret_number[:9]]
                chiffres[1::2] = [chiffre * 2 for chiffre in chiffres[1::2]]
                chiffres = [chiffre - 9 if chiffre > 9 else chiffre for chiffre in chiffres]
                total = sum(chiffres)
            except ValueError:
                raise validators.ValidationError(_('A siret number is only made of digits'))

            if not total % 10 == 0:
                raise validators.ValidationError(_('Invalid Siret number'))


class OrganizationForm(ModelForm):
    model_class = Organization

    name = fields.StringField(_('Name'), [validators.DataRequired(), validators.Length(max=TITLE_SIZE_LIMIT)])
    acronym = fields.StringField(
        _('Acronym'), description=_('Shorter organization name'))
    description = fields.MarkdownField(
        _('Description'), [validators.DataRequired(), validators.Length(max=DESCRIPTION_SIZE_LIMIT)],
        description=_('The details about your organization'))
    url = fields.URLField(
        _('Website'), description=_('The organization website URL'))
    logo = fields.ImageField(_('Logo'), sizes=LOGO_SIZES)
    business_number_id = fields.StringField(_('Business id'), [org_bid_check],
                                            description=_('Business identification number'))

    deleted = fields.DateTimeField()
    extras = fields.ExtrasField()

    def save(self, commit=True, **kwargs):
        '''Register the current user as admin on creation'''
        org = super(OrganizationForm, self).save(commit=False, **kwargs)

        if not org.id:
            user = current_user._get_current_object()
            member = Member(user=user, role='admin')
            org.members.append(member)
            org.count_members()

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
        _('Role'), default='editor', choices=list(ORG_ROLES.items()),
        validators=[validators.DataRequired()])
