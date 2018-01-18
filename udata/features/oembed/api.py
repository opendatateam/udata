# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import current_app

from udata import theme
from udata.api import api, API
from udata.models import db, Dataset, GeoZone, TERRITORY_DATASETS

oembeds_parser = api.parser()
oembeds_parser.add_argument(
    'references', help='References of the resources to embed.',
    location='args', required=True)


@api.route('/oembeds/', endpoint='oembeds')
class OEmbedsAPI(API):

    @api.doc('oembeds', parser=oembeds_parser)
    def get(self):
        """ The returned payload is a list of OEmbed formatted responses.

        See: http://oembed.com/

        The `references` are composed by a keyword (`kind`) followed by
        the `id` each of those separated by commas.
        E.g:
        dataset-5369992aa3a729239d205183,
        territory-fr:departement:33@1860-07-01:emploi_dep

        Only datasets and territories are supported for now.
        """
        args = oembeds_parser.parse_args()
        references = args['references'].split(',')
        result = []
        for item_reference in references:
            try:
                item_kind, item_id = item_reference.split('-', 1)
            except ValueError:
                return api.abort(400, 'Invalid ID.')
            if item_kind == 'dataset':
                try:
                    item = Dataset.objects.get(id=item_id)
                except (db.ValidationError, Dataset.DoesNotExist):
                    return api.abort(400, 'Unknown dataset ID.')
            elif (item_kind == 'territory' and
                    current_app.config.get('ACTIVATE_TERRITORIES')):

                try:
                    country, level, code, kind = item_id.split(':')
                except ValueError:
                    return api.abort(400, 'Invalid territory ID.')
                geoid = ':'.join((country, level, code))
                zone = GeoZone.objects.resolve(geoid)
                if not zone:
                    return api.abort(400, 'Unknown territory identifier.')
                if level in TERRITORY_DATASETS:
                    if kind in TERRITORY_DATASETS[level]:
                        item = TERRITORY_DATASETS[level][kind](zone)
                    else:
                        return api.abort(400, 'Unknown territory dataset id.')
                else:
                    return api.abort(400, 'Unknown kind of territory.')
            else:
                return api.abort(400, 'Invalid object type.')
            width = maxwidth = 1000
            height = maxheight = 200
            html = theme.render('embed-dataset.html', **{
                'width': width,
                'height': height,
                'item': item,
                'item_reference': item_reference,
            })
            result.append({
                'type': 'rich',
                'version': '1.0',
                'html': html,
                'width': width,
                'height': height,
                'maxwidth': maxwidth,
                'maxheight': maxheight,
            })
        return result
