import geojson
import json
import logging

from udata.forms import widgets, ModelForm, validators
from udata.forms.fields import ModelList, Field, SelectField, FormField
from udata.i18n import lazy_gettext as _

from .models import GeoZone, SpatialCoverage, spatial_granularities

log = logging.getLogger(__name__)


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


class ZonesField(ModelList, Field):
    model = GeoZone
    widget = ZonesAutocompleter()

    def fetch_objects(self, geoids):
        '''
        Custom object retrieval.

        Zones are resolved from their identifier
        instead of the default bulk fetch by ID.
        '''
        zones = []
        no_match = []
        for geoid in geoids:
            zone = GeoZone.objects.resolve(geoid)
            if zone:
                zones.append(zone)
            else:
                no_match.append(geoid)

        if no_match:
            msg = _('Unknown geoid(s): {identifiers}').format(
                identifiers=', '.join(str(id) for id in no_match))
            raise validators.ValidationError(msg)

        return zones


class GeomField(Field):
    def process_formdata(self, valuelist):
        if valuelist:
            value = valuelist[0]
            try:
                if isinstance(value, str):
                    self.data = geojson.loads(value)
                else:
                    self.data = geojson.GeoJSON.to_instance(value)
            except:
                self.data = None
                log.exception('Unable to parse GeoJSON')
                raise ValueError(self.gettext('Not a valid GeoJSON'))

    def pre_validate(self, form):
        if self.data:
            if not isinstance(self.data, geojson.GeoJSON):
                raise validators.ValidationError('Not a valid GeoJSON')
            if not self.data.is_valid:
                raise validators.ValidationError(self.data.errors())
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
