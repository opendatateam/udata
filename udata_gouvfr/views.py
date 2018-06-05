# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for, redirect, abort
from jinja2.exceptions import TemplateNotFound

from udata import theme
from udata.models import Reuse, Organization, Dataset
from udata.i18n import I18nBlueprint
from udata.sitemap import sitemap

from .models import (
    DATACONNEXIONS_5_CANDIDATE, C3, NECMERGITUR, OPENFIELD16, SPD
)


blueprint = I18nBlueprint('gouvfr', __name__,
                          template_folder='templates',
                          static_folder='static',
                          static_url_path='/static/gouvfr')


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


@blueprint.route('/dataconnexions/')
def dataconnexions():
    '''Redirect to latest dataconnexions edition page'''
    return redirect(url_for('gouvfr.dataconnexions6'))


DATACONNEXIONS_5_CATEGORIES = [
    ('datadmin', 'Datadmin', (
        'Projets portés par un acteur public (administration centrale ou '
        'déconcentrée, collectivité...) qui a utilisé l’open data pour '
        'améliorer son action, pour résoudre un problème…'
    )),
    ('data2b', 'Data-2-B', 'Projets destinés à un usage professionnel'),
    ('data2c', 'Data-2-C', 'Projets destinés au grand public'),
    ('datautile', 'Data-utile', (
        'Projets d’intérêt général, engagés par exemple dans les champs de '
        'la solidarité, du développement durable ou de la lutte contre '
        'les discriminations, ou portés par une association, une ONG, '
        'une entreprise sociale, un entrepreneur social ou un citoyen.'
    )),
    ('datajournalisme', 'Data-journalisme',
     'Projets s’inscrivants dans la thématique du journalisme de données.'),
]


DATACONNEXIONS_6_CATEGORIES = [
    ('impact-demo', 'Impact démocratique', (
        'Projets destinés à renforcer la transparence et la participation '
        'dans une logique de co-production pour un gouvernement ouvert.')),
    ('impact-soc', 'Impact social et environnemental', (
        'Projets qui contribuent à la résolution de problématiques sociales '
        '(éducation, santé, emploi, pauvreté, exclusion) '
        '- ou environnementales.')),
    ('impact-eco', 'Impact économique et scientifique', (
        'Projets créateurs de valeur économique ou scientifique à travers des '
        'nouveaux produits ou services qui visent le grand public, '
        'le monde professionnel ou la recherche.')),
    ('impact-adm', 'Impact administratif et territorial', (
        'Projets destinés à renforcer l’efficacité, la visibilité '
        'et la mise en réseau des administrations, des collectivités et '
        'des communautés territoriales.')),
]


@blueprint.route('/dataconnexions-5')
def dataconnexions5():
    reuses = Reuse.objects(badges__kind=DATACONNEXIONS_5_CANDIDATE).visible()

    categories = [{
        'tag': tag,
        'label': label,
        'description': description,
        'reuses': reuses(tags=tag),
    } for tag, label, description in DATACONNEXIONS_5_CATEGORIES]
    return theme.render('dataconnexions-5.html', categories=categories)


@blueprint.route('/dataconnexions-6')
def dataconnexions6():
    # Use tags until we are sure all reuse are correctly labeled
    # reuses = Reuse.objects(badges__kind=DATACONNEXIONS_6_CANDIDATE)
    reuses = Reuse.objects(tags='dataconnexions-6').visible()

    categories = [{
        'tag': tag,
        'label': label,
        'description': description,
        'reuses': reuses(tags=tag),
    } for tag, label, description in DATACONNEXIONS_6_CATEGORIES]
    return theme.render('dataconnexions-6.html', categories=categories)


C3_PARTNERS = (
    'institut-national-de-l-information-geographique-et-forestiere',
    'meteo-france',
    'etalab',
    'ministere-de-l-ecologie-du-developpement-durable-et-de-l-energie',
    'museum-national-dhistoire-naturelle',
    'irstea',
    'electricite-reseau-distribution-france',
)
NB_DISPLAYED_DATASETS = 18


@blueprint.route('/c3')
def c3():
    return redirect(url_for('gouvfr.climate_change_challenge'))


@blueprint.route('/climate-change-challenge')
def climate_change_challenge():
    partners = Organization.objects(slug__in=C3_PARTNERS)
    datasets = (Dataset.objects(badges__kind=C3).visible()
                .order_by('-metrics.followers'))
    return theme.render('c3.html',
                        partners=partners,
                        datasets=datasets,
                        badge=C3,
                        nb_displayed_datasets=NB_DISPLAYED_DATASETS)


@blueprint.route('/nec-mergitur')
def nec_mergitur():
    datasets = (Dataset.objects(badges__kind=NECMERGITUR).visible()
                .order_by('-metrics.followers'))
    return theme.render('nec_mergitur.html',
                        datasets=datasets,
                        badge=NECMERGITUR,
                        nb_displayed_datasets=NB_DISPLAYED_DATASETS)


@blueprint.route('/openfield16')
def openfield16():
    datasets = (Dataset.objects(badges__kind=OPENFIELD16).visible()
                .order_by('-metrics.followers'))
    return theme.render('openfield16.html',
                        datasets=datasets,
                        badge=OPENFIELD16,
                        nb_displayed_datasets=NB_DISPLAYED_DATASETS)


@blueprint.route('/reference')
def spd():
    datasets = Dataset.objects(badges__kind=SPD).order_by('title')
    return theme.render('spd.html', datasets=datasets, badge=SPD)


@blueprint.route('/licences')
def licences():
    try:
        return theme.render('licences.html')
    except TemplateNotFound:
        abort(404)


@blueprint.route('/suivi')
def suivi():
    try:
        return theme.render('suivi.html')
    except TemplateNotFound:
        abort(404)


@blueprint.route('/faq/', defaults={'section': 'home'})
@blueprint.route('/faq/<string:section>/')
def faq(section):
    try:
        return theme.render('faq/{0}.html'.format(section), page_name=section)
    except TemplateNotFound:
        abort(404)


@sitemap.register_generator
def gouvfr_sitemap_urls():
    yield 'gouvfr.faq_redirect', {}, None, 'weekly', 1
    for section in ('citizen', 'producer', 'reuser', 'developer',
                    'system-integrator'):
        yield 'gouvfr.faq_redirect', {'section': section}, None, 'weekly', 0.7
    yield 'gouvfr.dataconnexions_redirect', {}, None, 'monthly', 0.4
    yield 'gouvfr.redevances_redirect', {}, None, 'yearly', 0.4
