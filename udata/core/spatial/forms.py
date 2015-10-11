# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from udata.forms import widgets, ModelForm
from udata.forms.fields import ModelList, StringField, SelectField, FormField
from udata.i18n import lazy_gettext as _

from .models import GeoZone, SpatialCoverage, spatial_granularities


class ZonesAutocompleter(widgets.TextInput):
    classes = 'zone-completer'

    def __call__(self, field, **kwargs):
        '''Store the values as JSON to prefeed selectize'''
        if field.data:
            kwargs['data-values'] = json.dumps([{
                'id': zone.id,
                'name': zone.name
            } for zone in field.data])
        return super(ZonesAutocompleter, self).__call__(field, **kwargs)


class ZonesField(ModelList, StringField):
    model = GeoZone
    widget = ZonesAutocompleter()


class SpatialCoverageForm(ModelForm):
    model_class = SpatialCoverage

    zones = ZonesField(_('Spatial coverage'),
                       description=_('A list of covered territories'),
                       default=[])
    granularity = SelectField(_('Spatial granularity'),
                              description=_('The size of the data increment'),
                              choices=lambda: spatial_granularities,
                              default='other')


class SpatialCoverageField(FormField):
    def __init__(self, *args, **kwargs):
        super(SpatialCoverageField, self).__init__(SpatialCoverageForm,
                                                   *args,
                                                   **kwargs)
