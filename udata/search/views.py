# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata import search, theme
from udata.models import Dataset, Organization, Reuse
from udata.utils import not_none_dict
from udata.features.territories import check_for_territories
from udata.i18n import I18nBlueprint

blueprint = I18nBlueprint('search', __name__)

# Maps template variables names to model types
MAPPING = {
    'datasets': Dataset,
    'reuses': Reuse,
    'organizations': Organization,
}


@blueprint.route('/search/', endpoint='index')
def render_search():
    # We only fetch relevant data for the given filter.
    # To do so, we parse query for each type
    # and we only keep types supporting all parameters
    adapters = {t: search.adapter_for(m) for t, m in MAPPING.items()}
    type_args = {
        t: not_none_dict(a.as_request_parser().parse_args())
        for t, a in adapters.items()
    }
    all_args = set.union(*[
        set(args.keys()) for args in type_args.values()
    ])
    types = [
        typ for typ, args in type_args.items()
        if set(args.keys()) == all_args
    ]
    params = type_args[types[0]]
    params['facets'] = True
    models = [MAPPING[typ] for typ in types]
    results = search.multisearch(*models, **params)
    context = dict(zip(types, results))
    territories = check_for_territories(params.get('q'))
    context['territories'] = territories
    return theme.render('search.html', **context)
