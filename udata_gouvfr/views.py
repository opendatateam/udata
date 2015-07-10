# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for, redirect

from udata import theme
from udata.models import Reuse, Organization, Dataset, DATACONNEXIONS_CANDIDATE
from udata.core.dataset.models import C3
from udata.i18n import I18nBlueprint
from udata.sitemap import sitemap


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
    reuses = Reuse.objects(badges__kind=DATACONNEXIONS_CANDIDATE)

    categories = [{
        'tag': tag,
        'label': label,
        'description': description,
        'reuses': reuses(tags=tag),
    } for tag, label, description in DATACONNEXIONS_CATEGORIES]
    return theme.render('dataconnexions.html', categories=categories)


C3_PARTNERS = (
    'institut-national-de-l-information-geographique-et-forestiere',
    'meteo-france',
    'etalab',
    'ministere-de-l-ecologie-du-developpement-durable-et-de-l-energie',
    'museum-national-dhistoire-naturelle',
)


@blueprint.route('/c3')
def c3():
    return redirect(url_for('gouvfr.climate_change_challenge'))


@blueprint.route('/climate-change-challenge')
def climate_change_challenge():
    partners = Organization.objects(slug__in=C3_PARTNERS)
    datasets = Dataset.objects(badges__kind=C3)
    return theme.render('c3.html', partners=partners, datasets=datasets)


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


@sitemap.register_generator
def gouvfr_sitemap_urls():
    yield 'gouvfr.faq_redirect', {}, None, 'weekly', 1
    for section in ('citizen', 'producer', 'reuser', 'developer'):
        yield 'gouvfr.faq_redirect', {'section': section}, None, 'weekly', 0.7
    yield 'gouvfr.dataconnexions_redirect', {}, None, 'monthly', 0.4
    yield 'gouvfr.redevances_redirect', {}, None, 'yearly', 0.4
    yield 'gouvfr.terms_redirect', {}, None, 'monthly', 0.2
    yield 'gouvfr.credits_redirect', {}, None, 'monthly', 0.2
