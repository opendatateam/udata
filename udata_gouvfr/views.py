# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pkg_resources import resource_stream


from flask import abort, url_for, redirect, json

from udata.frontend import render
from udata.models import Dataset, Reuse
from udata.i18n import I18nBlueprint


blueprint = I18nBlueprint('gouvfr', __name__, template_folder='templates', static_folder='static')


@blueprint.route('/dataset/<dataset>/')
def redirect_datasets(dataset):
    '''Route Legacy CKAN datasets'''
    return redirect(url_for('datasets.show', dataset=dataset))


@blueprint.route('/DataSet/<legacy_id>')
def redirect_datasets_v1(legacy_id):
    '''Route legacy v1 datasets'''
    with resource_stream(__name__, 'legacy-datasets.json') as f:
        slug = json.load(f).get(legacy_id)
    if not slug:
        abort(404)
    return redirect(url_for('datasets.show', dataset=slug))


@blueprint.route('/organization/')
def redirect_organizations_list():
    '''Route legacy CKAN organizations listing'''
    return redirect(url_for('organizations.list'))


@blueprint.route('/organization/<org>/')
def redirect_organizations(org):
    '''Route legacy CKAN organizations'''
    return redirect(url_for('organizations.show', org=org))


@blueprint.route('/group/<topic>/')
def redirect_topics(topic):
    '''Route legacy CKAN topics'''
    return redirect(url_for('topics.display', topic=topic))


@blueprint.route('/Redevances')
def redevances():
    return render('redevances.html')


@blueprint.route('/developer')
def developer():
    return render('developer.html')


DATACONNEXIONS_TAG = 'dataconnexions'

DATACONNEXIONS_CATEGORIES = [
    ('datadmin', 'Datadmin', (
        'Projets portés par un acteur public (administration centrale ou déconcentrée, collectivité...) '
        'qui a utilisé l’open data pour améliorer son action, pour résoudre un problème...'
    )),
    ('data2b', 'Data-2-B', 'Projets destinés à un usage professionnel'),
    ('data2c', 'Data-2-C', 'Projets destinés au grand public'),
    ('datautile', 'Data-utile', (
        'Projets d’intérêt général, engagés par exemple dans les champs de la solidarité, '
        'du développement durable ou de la lutte contre les discriminations, '
        'ou portés par une association, une ONG, une entreprise sociale, un entrepreneur social ou un citoyen.'
    )),
    ('datajournalisme', 'Data-journalisme', 'Projets s’inscrivants dans la thématique du journalisme de données.'),
]


@blueprint.route('/dataconnexions')
def dataconnexions():
    reuses = Reuse.objects(tags=DATACONNEXIONS_TAG)

    categories = [{
        'tag': tag,
        'label': label,
        'description': description,
        'reuses': reuses(tags=tag),
    } for tag, label, description in DATACONNEXIONS_CATEGORIES]
    return render('dataconnexions.html', categories=categories)
