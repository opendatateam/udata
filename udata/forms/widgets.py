# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from wtforms import widgets

from jinja2 import Markup
from werkzeug.utils import escape

from udata.frontend.helpers import placeholder
from udata.i18n import gettext as _

# _ = lambda s: s

MIN_TAG_LENGTH = 2
MAX_TAG_LENGTH = 50


class WidgetHelper(object):
    classes = []
    attributes = {}

    def __call__(self, field, **kwargs):
        # Handle extra classes
        classes = (kwargs.pop('class', '') or kwargs.pop('class_', '')).split()
        extra_classes = self.classes if isinstance(self.classes, (list, tuple)) else [self.classes]
        classes.extend([cls for cls in extra_classes if cls not in classes])
        kwargs['class'] = ' '.join(classes)

        # Handle defaults
        for key, value in self.attributes.items():
            kwargs.setdefault(key, value)

        return super(WidgetHelper, self).__call__(field, **kwargs)


class TextArea(WidgetHelper, widgets.TextArea):
    pass


class SelectPicker(WidgetHelper, widgets.Select):
    classes = 'selectpicker'


class MarkdownEditor(WidgetHelper, widgets.TextArea):
    classes = 'md'
    attributes = {'rows': 8}


class FormatAutocompleter(WidgetHelper, widgets.TextInput):
    classes = 'format-completer'


class TerritoryAutocompleter(WidgetHelper, widgets.TextInput):
    classes = 'territory-completer'

    def __call__(self, field, **kwargs):
        '''Store the values as JSON to prefeed selectize'''
        if field.data:
            kwargs['data-values'] = json.dumps([{
                'id': str(territory.id),
                'name': territory.name
            } for territory in field.data])
        return super(TerritoryAutocompleter, self).__call__(field, **kwargs)


class DatasetAutocompleter(WidgetHelper, widgets.TextInput):
    classes = 'dataset-completer'

    def __call__(self, field, **kwargs):
        '''Store the values as JSON to prefeed selectize'''
        if field.data:
            kwargs['data-values'] = json.dumps([{
                'id': str(dataset.id),
                'title': getattr(dataset, 'title', ''),
            } for dataset in field.data])
        return super(DatasetAutocompleter, self).__call__(field, **kwargs)


class ReuseAutocompleter(WidgetHelper, widgets.TextInput):
    classes = 'reuse-completer'

    def __call__(self, field, **kwargs):
        '''Store the values as JSON to prefeed selectize'''
        if field.data:
            kwargs['data-values'] = json.dumps([{
                'id': str(reuse.id),
                'title': getattr(reuse, 'title', ''),
            } for reuse in field.data])
        return super(ReuseAutocompleter, self).__call__(field, **kwargs)


class TagAutocompleter(WidgetHelper, widgets.TextInput):
    classes = 'tag-completer'
    attributes = {
        'data-tag-minlength': MIN_TAG_LENGTH,
        'data-tag-maxlength': MAX_TAG_LENGTH,
    }


class TopicAutocompleter(WidgetHelper, widgets.TextInput):
    classes = 'topic-completer'


class KeyValueWidget(WidgetHelper, widgets.TextInput):
    pass


class DateRangePicker(WidgetHelper, widgets.HiddenInput):
    classes = 'dtpicker'

    def __call__(self, field, **kwargs):
        if field.data:
            kwargs['data-start-date'] = field.data.start
            kwargs['data-end-date'] = field.data.end
        return super(DateRangePicker, self).__call__(field, **kwargs)


class UploadableURL(WidgetHelper, widgets.html5.URLInput):
    # classes = 'uploadable-url'

    def __call__(self, field, **kwargs):
        kwargs['data-endpoint'] = field.endpoint
        return super(UploadableURL, self).__call__(field, **kwargs)


class ImageURL(WidgetHelper, widgets.html5.URLInput):
    # classes = 'uploadable-url'

    def __call__(self, field, **kwargs):
        kwargs['data-endpoint'] = field.endpoint
        return super(ImageURL, self).__call__(field, **kwargs)


class ImagePicker(object):
    def __call__(self, field, **kwargs):
        sizes = ','.join(str(s) for s in field.sizes)
        default_img = placeholder(None, field.placeholder)
        html = [
            '<div class="image-picker-field" data-sizes="{0}" data-basename="{1}" data-endpoint="{2}">'.format(
                sizes, field.name, field.endpoint
            ),
            '<div class="image-picker-preview">',
            '<img src="{0}" data-placeholder="{1}"/>'.format(field.src or default_img, default_img),
            '</div>',
            '<span class="image-picker-btn btn btn-default btn-file">',
            _('Choose a picture'),
            field.filename(),
            field.bbox(),
            '</span>',
            '</div>'
        ]
        return widgets.HTMLString(''.join(html))
