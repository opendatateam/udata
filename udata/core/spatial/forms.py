# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import geojson

from udata.forms import widgets, ModelForm, validators
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


class GeomField(StringField):
    def process_formdata(self, valuelist):
        if valuelist:
            value = valuelist[0]
            try:
                if isinstance(value, basestring):
                    self.data = geojson.loads(value)
                else:
                    self.data = geojson.GeoJSON.to_instance(value)
            except:
                self.data = None
                raise ValueError(self.gettext('Not a valid GeoJSON'))

    def pre_validate(self, form):
        if self.data:
            result = geojson.is_valid(self.data)
            if result['valid'] == 'no':
                raise validators.ValidationError(result['message'])
        return True


class SpatialCoverageForm(ModelForm):
    model_class = SpatialCoverage

    zones = ZonesField(_('Spatial coverage'),
                       description=_('A list of covered territories'),
                       default=[])
    granularity = SelectField(_('Spatial granularity'),
                              description=_('The size of the data increment'),
                              choices=lambda: spatial_granularities,
                              default='other')
    geom = GeomField()


class SpatialCoverageField(FormField):
    def __init__(self, *args, **kwargs):
        super(SpatialCoverageField, self).__init__(SpatialCoverageForm,
                                                   *args,
                                                   **kwargs)
