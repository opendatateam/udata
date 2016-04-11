# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.i18n import lazy_gettext as _
from udata.models import (
    db, Dataset, User, Organization, Reuse,
    TerritoryDataset, ResourceBasedTerritoryDataset,
    TERRITORY_DATASETS
)

Dataset.extras.register('datagouv_ckan_last_sync', db.DateTimeField)
Organization.extras.register('datagouv_ckan_last_sync', db.DateTimeField)
Reuse.extras.register('datagouv_ckan_last_sync', db.DateTimeField)
User.extras.register('datagouv_ckan_last_sync', db.DateTimeField)

# Reuses badges
DATACONNEXIONS_5_CANDIDATE = 'dataconnexions-5-candidate'
DATACONNEXIONS_5_LAUREATE = 'dataconnexions-5-laureate'
DATACONNEXIONS_6_CANDIDATE = 'dataconnexions-6-candidate'
DATACONNEXIONS_6_LAUREATE = 'dataconnexions-6-laureate'
Reuse.__badges__.update({
    DATACONNEXIONS_5_CANDIDATE: _('Dataconnexions 5 candidate'),
    DATACONNEXIONS_5_LAUREATE: _('Dataconnexions 5 laureate'),
    DATACONNEXIONS_6_CANDIDATE: _('Dataconnexions 6 candidate'),
    DATACONNEXIONS_6_LAUREATE: _('Dataconnexions 6 laureate'),
})

# Datasets
C3 = 'c3'
NECMERGITUR = 'nec'
Dataset.__badges__[C3] = _('C³')
Dataset.__badges__[NECMERGITUR] = _('Nec Mergitur')


class ZonagesTownDataset(TerritoryDataset):
    order = 8
    id = 'zonages'
    title = 'Zonages des politiques de la ville'
    # Ministère de l'Egalité des Territoires et du Logement.
    organization_id = '534fff8fa3a7292c64a77f3d'
    url_template = (
        'http://sig.ville.gouv.fr/Territoire/{code}/onglet/DonneesLocales')
    description = '''
        [ZFU](/datasets/presence-dans-la-commune-d-une-zone-franche-urbaine-zfu-30382923/),
        [ZUS](/datasets/presence-dans-la-commune-d-une-zone-urbaine-sensible-zus-30382883/),
        et autres quartiers du
        [CUCS](/datasets/contrat-urbain-de-cohesion-sociale-cucs-30382914/).
    '''.strip()


class ComptesTownDataset(TerritoryDataset):
    order = 9
    id = 'comptes'
    title = 'Comptes de la collectivité'
    # Ministère des finances et des comptes publics.
    organization_id = '534fff8ea3a7292c64a77f02'
    url_template = (
        'http://alize2.finances.gouv.fr/communes/eneuro/tableau.php'
        '?icom={icom}&dep=0{dep}&type=BPS&param=0')
    description = '''
        Chiffres Clés, fonctionnement, investissement, fiscalité,
        autofinancement, endettement.
    '''.strip()
    temporal_coverage = {
        'start': 2000,
        'end': 2014
    }
    license_id = 'notspecified'

    @property
    def url(self):
        return self.url_template.format(icom=self.territory.code[2:5],
                                        dep=self.territory.code[0:2])


class LogementTownDataset(TerritoryDataset):
    order = 6
    id = 'logement'
    title = 'Logement'
    # Institut National de la Statistique et des Etudes Economiques (INSEE).
    organization_id = '534fff81a3a7292c64a77e5c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=LOG&nivgeo=COM&codgeo={code}')
    description = '''
        [Chiffres clés
        ](/datasets/recensement-de-la-population-base-de-donnees-de-chiffres-cles-logement-40535148/)
        logement.
    '''.strip()
    temporal_coverage = {
        'start': 2007,
        'end': 2012
    }


class EmploiPopulationTownDataset(TerritoryDataset):
    order = 5
    id = 'emploi_population'
    title = 'Emploi - Population active'
    # Institut National de la Statistique et des Etudes Economiques (INSEE).
    organization_id = '534fff81a3a7292c64a77e5c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=EMP&nivgeo=COM&codgeo={code}')
    description = '''
        [Population
        ](/datasets/recensement-de-la-population-base-de-donnees-de-chiffres-cles-emploi-population-active-40535210/)
        de 15 à 64 ans par type d’activité.
    '''.strip()
    temporal_coverage = {
        'start': 2007,
        'end': 2012
    }


class EmploiChiffresTownDataset(TerritoryDataset):
    order = 4
    id = 'emploi_chiffres'
    title = 'Emploi - Chiffres clés'
    # Institut National de la Statistique et des Etudes Economiques (INSEE).
    organization_id = '534fff81a3a7292c64a77e5c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=ACT&nivgeo=COM&codgeo={code}')
    description = '''
        [Population
        ](/datasets/recensement-de-la-population-base-de-donnees-de-chiffres-cles-caracteristiques-de-l-emploi-40535204/)
        de 15 ans ou plus ayant un emploi selon le statut.
    '''.strip()
    temporal_coverage = {
        'start': 2007,
        'end': 2012
    }


class PopulationTownDataset(TerritoryDataset):
    order = 1
    id = 'population'
    title = 'Population'
    # Institut National de la Statistique et des Etudes Economiques (INSEE).
    organization_id = '534fff81a3a7292c64a77e5c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=POP&nivgeo=COM&codgeo={code}')
    description = '''
        [Population](/datasets/population/)
        par sexe et âge, indicateurs démographiques.
    '''.strip()
    temporal_coverage = {
        'start': 2007,
        'end': 2012
    }


class PopulationChiffresTownDataset(TerritoryDataset):
    order = 2
    id = 'population_chiffres'
    title = 'Population - Chiffres clés'
    # Institut National de la Statistique et des Etudes Economiques (INSEE).
    organization_id = '534fff81a3a7292c64a77e5c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=FAM&nivgeo=COM&codgeo={code}')
    description = '''
        [Ménages, couples, familles
        ](/datasets/recensement-de-la-population-base-de-donnees-de-chiffres-cles-evolution-et-structure-de-la--40535162/)
        selon leur composition.
    '''.strip()
    temporal_coverage = {
        'start': 2007,
        'end': 2012
    }


class PopulationDiplomesTownDataset(TerritoryDataset):
    order = 3
    id = 'population_diplomes'
    title = 'Population - Diplômes et formations'
    # Institut National de la Statistique et des Etudes Economiques (INSEE).
    organization_id = '534fff81a3a7292c64a77e5c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=FOR&nivgeo=COM&codgeo={code}')
    description = '''
        [Scolarisation
        ](/datasets/recensement-de-la-population-base-de-donnees-de-chiffres-cles-diplomes-formation-40535144/)
        selon l’âge et le sexe.
    '''.strip()
    temporal_coverage = {
        'start': 2007,
        'end': 2012
    }


class ElectionsRegionales2015Tour2TownDataset(
        ResourceBasedTerritoryDataset):
    order = 7
    id = 'elections_regionales_2015_2'
    title = 'Élections régionales 2015, second tour'
    # Ministère de l'Intérieur.
    organization_id = '534fff91a3a7292c64a77f53'
    description = '''
        [Résultats
        ](/datasets/elections-regionales-2015-et-des-assemblees-de-corse-de-guyane-et-de-martinique-resultats-par-bureaux-de-vote-tour-2/)
        par bureau de vote pour la commune concernée.
    '''.strip()
    # Equals to: https://www.data.gouv.fr/fr/datasets/elections-regionales-2015
    # -et-des-assemblees-de-corse-de-guyane-et-de-martinique-resultats-par-
    # bureaux-de-vote-tour-2/
    dataset_id = '56728d35c751df240dc664bd'
    resource_id = 'e915b43b-f38c-4f18-ade5-2fb6c8cf80ca'
    territory_attr = 'name'
    csv_column = 'LIBSUBCOM'
    temporal_coverage = {
        'start': 2015
    }


class BanODBLTownDataset(TerritoryDataset):
    order = 10
    id = 'ban_odbl'
    title = 'Adresses'
    # Etalab.
    organization_id = '534fff75a3a7292c64a77de4'
    url_template = ('http://bano.openstreetmap.fr/BAN_odbl/communes/'
                    'BAN_odbl_{code}.csv')
    description = '''
        Données de la [Base Adresse Nationale
        ](/datasets/ban-base-adresse-nationale/)
        sur le périmètre de la commune.
    '''.strip()


TERRITORY_DATASETS.update({
    'zonages': ZonagesTownDataset,
    'comptes': ComptesTownDataset,
    'logement': LogementTownDataset,
    'emploi_population': EmploiPopulationTownDataset,
    'emploi_chiffres': EmploiChiffresTownDataset,
    'population': PopulationTownDataset,
    'population_chiffres': PopulationChiffresTownDataset,
    'population_diplomes': PopulationDiplomesTownDataset,
    'elections_regionales_2015_2': ElectionsRegionales2015Tour2TownDataset,
    'ban_odbl': BanODBLTownDataset
})
