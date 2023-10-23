from udata.forms import ModelForm, fields, validators
from udata.i18n import lazy_gettext as _
from udata.models import Reuse, REUSE_TYPES, REUSE_TOPICS

from .models import IMAGE_SIZES, TITLE_SIZE_LIMIT, DESCRIPTION_SIZE_LIMIT

__all__ = ('ReuseForm', )


def check_url_does_not_exists(form, field):
    '''Ensure a reuse URL is not yet registered'''
    if field.data != field.object_data and Reuse.url_exists(field.data):
        raise validators.ValidationError(_('This URL is already registered'))


class ReuseForm(ModelForm):
    model_class = Reuse

    title = fields.StringField(_('Title'), [validators.DataRequired(), validators.Length(max=TITLE_SIZE_LIMIT)])
    description = fields.MarkdownField(
        _('Description'), [validators.DataRequired(), validators.Length(max=DESCRIPTION_SIZE_LIMIT)],
        description=_('The details about the reuse (build process, specifics, '
                      'self-critics...).'))
    type = fields.SelectField(_('Type'), choices=list(REUSE_TYPES.items()))
    url = fields.URLField(
        _('URL'), [validators.DataRequired(), check_url_does_not_exists])
    image = fields.ImageField(
        _('Image'), sizes=IMAGE_SIZES, placeholder='reuse')
    tags = fields.TagField(_('Tags'), description=_('Some taxonomy keywords'))
    datasets = fields.DatasetListField(_('Used datasets'))
    private = fields.BooleanField(
        _('Private'),
        description=_('Restrict the dataset visibility to you or '
                      'your organization only.'))
    topic = fields.SelectField(_('Topic'), choices=list(REUSE_TOPICS.items()))

    owner = fields.CurrentUserField()
    organization = fields.PublishAsField(_('Publish as'))
    deleted = fields.DateTimeField()
    extras = fields.ExtrasField()
