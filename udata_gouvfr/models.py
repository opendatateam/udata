# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.i18n import lazy_gettext as _
from udata.models import (
    db, Dataset, User, Organization, Reuse,
    TerritoryDataset, ResourceBasedTerritoryDataset
)

__all__ = ('TERRITORY_DATASETS',)

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


class ZonagesTerritoryDataset(TerritoryDataset):
    id = 'zonages'
    title = 'Zonages des politiques de la ville'
    organization_id = '534fff8fa3a7292c64a77f3d'
    url_template = 'http://sig.ville.gouv.fr/Cartographie/{code}'
    description = '''
        ZFU, ZUS, et autres quartiers du CUCS. Source :
        Ministère de l’égalité des territoires et du logement.
    '''.strip()


class ComptesTerritoryDataset(TerritoryDataset):
    id = 'comptes'
    title = 'Comptes de la collectivité'
    organization_id = '534fff8ea3a7292c64a77f02'
    url_template = (
        'http://alize2.finances.gouv.fr/communes/eneuro/tableau.php'
        '?icom={icom}&dep=0{dep}&type=BPS&param=0')
    description = '''
        Chiffres Clés, Fonctionnement, Investissement, Fiscalité,
        Autofinancement, Endettement (source Ministère des Finances).
    '''.strip()
    temporal_coverage = {
        'start': 2000,
        'end': 2014
    }

    @property
    def url(self):
        return self.url_template.format(icom=self.territory.code[2:5],
                                        dep=self.territory.code[0:2])


class LogementTerritoryDataset(TerritoryDataset):
    id = 'logement'
    title = 'Logement'
    organization_id = '534fff81a3a7292c64a77e5c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=LOG&nivgeo=COM&codgeo={code}')
    description = '''
        Chiffres clés Logement (source INSEE).
    '''.strip()
    temporal_coverage = {
        'start': 2007,
        'end': 2012
    }


class EmploiPopulationTerritoryDataset(TerritoryDataset):
    id = 'emploi_population'
    title = 'Emploi - Population active'
    organization_id = '534fff81a3a7292c64a77e5c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=EMP&nivgeo=COM&codgeo={code}')
    description = '''
        Population de 15 à 64 ans par type d’activité (source INSEE).
    '''.strip()
    temporal_coverage = {
        'start': 2007,
        'end': 2012
    }


class EmploiChiffresTerritoryDataset(TerritoryDataset):
    id = 'emploi_chiffres'
    title = 'Emploi - Chiffres clés'
    organization_id = '534fff81a3a7292c64a77e5c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=ACT&nivgeo=COM&codgeo={code}')
    description = '''
        Population de 15 ans ou plus ayant un emploi selon le statut
        (source INSEE).
    '''.strip()
    temporal_coverage = {
        'start': 2007,
        'end': 2012
    }


class PopulationTerritoryDataset(TerritoryDataset):
    id = 'population'
    title = 'Population'
    organization_id = '534fff81a3a7292c64a77e5c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=POP&nivgeo=COM&codgeo={code}')
    description = '''
        Population par sexe et âge, indicateurs démographiques
        (données INSEE).
    '''.strip()
    temporal_coverage = {
        'start': 2007,
        'end': 2012
    }


class PopulationChiffresTerritoryDataset(TerritoryDataset):
    id = 'population_chiffres'
    title = 'Population - Chiffres clés'
    organization_id = '534fff81a3a7292c64a77e5c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=FAM&nivgeo=COM&codgeo={code}')
    description = '''
        Ménages, couples, familles selon leur composition
        (données INSEE).
    '''.strip()
    temporal_coverage = {
        'start': 2007,
        'end': 2012
    }


class PopulationDiplomesTerritoryDataset(TerritoryDataset):
    id = 'population_diplomes'
    title = 'Population - Diplômes et formations'
    organization_id = '534fff81a3a7292c64a77e5c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=FOR&nivgeo=COM&codgeo={code}')
    description = '''
        Scolarisation selon l’âge et le sexe
        (données INSEE).
    '''.strip()
    temporal_coverage = {
        'start': 2007,
        'end': 2012
    }


class ElectionsRegionales2015Tour2TerritoryDataset(
        ResourceBasedTerritoryDataset):
    id = 'elections_regionales_2015_2'
    title = 'Résultats des élections régionales 2015 (second tour)'
    organization_id = '534fff91a3a7292c64a77f53'
    description = '''
        Résultats par bureau de vote pour la commune concernée
        (données Ministère de l’Interieur).
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


TERRITORY_DATASETS = {
    'zonages': ZonagesTerritoryDataset,
    'comptes': ComptesTerritoryDataset,
    'logement': LogementTerritoryDataset,
    'emploi_population': EmploiPopulationTerritoryDataset,
    'emploi_chiffres': EmploiChiffresTerritoryDataset,
    'population': PopulationTerritoryDataset,
    'population_chiffres': PopulationChiffresTerritoryDataset,
    'population_diplomes': PopulationDiplomesTerritoryDataset,
    'elections_regionales_2015_2': ElectionsRegionales2015Tour2TerritoryDataset
}
