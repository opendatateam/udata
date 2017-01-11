# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from wtforms import widgets

MIN_TAG_LENGTH = 2
MAX_TAG_LENGTH = 50


class WidgetHelper(object):
    classes = []
    attributes = {}

    def __call__(self, field, **kwargs):
        # Handle extra classes
        classes = (kwargs.pop('class', '') or kwargs.pop('class_', '')).split()
        extra_classes = (
            self.classes
            if isinstance(self.classes, (list, tuple))
            else [self.classes]
        )
        classes.extend([cls for cls in extra_classes if cls not in classes])
        kwargs['class'] = ' '.join(classes)

        # Handle defaults
        for key, value in self.attributes.items():
            kwargs.setdefault(key, value)

        return super(WidgetHelper, self).__call__(field, **kwargs)


class TextInput(WidgetHelper, widgets.TextInput):
    pass


class TextArea(WidgetHelper, widgets.TextArea):
    pass


class SelectPicker(WidgetHelper, widgets.Select):
    classes = 'selectpicker'


class MarkdownEditor(WidgetHelper, widgets.TextArea):
    classes = 'md'
    attributes = {'rows': 8}


class DateRangePicker(WidgetHelper, widgets.HiddenInput):
    classes = 'dtpicker'

    def __call__(self, field, **kwargs):
        if field.data:
            kwargs['data-start-date'] = field.data.start
            kwargs['data-end-date'] = field.data.end
        return super(DateRangePicker, self).__call__(field, **kwargs)
