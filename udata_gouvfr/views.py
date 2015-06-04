# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for, redirect

from udata import theme
from udata.models import Reuse
from udata.i18n import I18nBlueprint


blueprint = I18nBlueprint('gouvfr', __name__, template_folder='templates', static_folder='static')


@blueprint.route('/dataset/<dataset>/')
def redirect_datasets(dataset):
    '''Route Legacy CKAN datasets'''
    return redirect(url_for('datasets.show', dataset=dataset))


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
    return theme.render('redevances.html')


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
    return theme.render('dataconnexions.html', categories=categories)


@blueprint.route('/faq/', defaults={'section': 'home'})
@blueprint.route('/faq/<string:section>/')
def faq(section):
    return theme.render('faq/{0}.html'.format(section))


@blueprint.route('/credits/')
def credits():
    return theme.render('credits.html')


@blueprint.route('/terms/')
def terms():
    return theme.render('terms.html')
