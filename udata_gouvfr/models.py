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
OPENFIELD16 = 'openfield16'
SPD = 'spd'
Dataset.__badges__[C3] = _('C³')
Dataset.__badges__[NECMERGITUR] = _('Nec Mergitur')
Dataset.__badges__[OPENFIELD16] = 'Openfield 16'
Dataset.__badges__[SPD] = _('Reference Data')


class PopulationDataset(TerritoryDataset):
    order = 1
    title = 'Population'
    # Institut National de la Statistique et des Etudes Economiques (INSEE).
    organization_id = '534fff81a3a7292c64a77e5c'
    description = '''
        [Population](/datasets/population/)
        par sexe et âge, indicateurs démographiques.
    '''.strip()
    temporal_coverage = {'start': 2007, 'end': 2012}


class PopulationTownDataset(PopulationDataset):
    id = 'population_t'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=POP&nivgeo=COM&codgeo={code}')


class PopulationCountyDataset(PopulationDataset):
    id = 'population_c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=POP&millesime=2012&typgeo=DEP&search={code}')


class PopulationRegionDataset(PopulationDataset):
    id = 'population_r'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=POP&millesime=2012&typgeo=REG&search={code}')


class PopulationChiffresDataset(TerritoryDataset):
    order = 2
    title = 'Population - Chiffres clés'
    # Institut National de la Statistique et des Etudes Economiques (INSEE).
    organization_id = '534fff81a3a7292c64a77e5c'
    description = '''
        [Ménages, couples, familles
        ](/datasets/recensement-de-la-population-base-de-donnees-de-chiffres-cles-evolution-et-structure-de-la--40535162/)
        selon leur composition.
    '''.strip()
    temporal_coverage = {'start': 2007, 'end': 2012}


class PopulationChiffresTownDataset(PopulationChiffresDataset):
    id = 'population_chiffres_t'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=FAM&nivgeo=COM&codgeo={code}')


class PopulationChiffresCountyDataset(PopulationChiffresDataset):
    id = 'population_chiffres_c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=FAM&millesime=2012&typgeo=DEP&search={code}')


class PopulationChiffresRegionDataset(PopulationChiffresDataset):
    id = 'population_chiffres_r'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=FAM&millesime=2012&typgeo=REG&search={code}')


class PopulationDiplomesDataset(TerritoryDataset):
    order = 3
    title = 'Population - Diplômes et formations'
    # Institut National de la Statistique et des Etudes Economiques (INSEE).
    organization_id = '534fff81a3a7292c64a77e5c'
    description = '''
        [Scolarisation
        ](/datasets/recensement-de-la-population-base-de-donnees-de-chiffres-cles-diplomes-formation-40535144/)
        selon l’âge et le sexe.
    '''.strip()
    temporal_coverage = {'start': 2007, 'end': 2012}


class PopulationDiplomesTownDataset(PopulationDiplomesDataset):
    id = 'population_diplomes_t'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=FOR&nivgeo=COM&codgeo={code}')


class PopulationDiplomesCountyDataset(PopulationDiplomesDataset):
    id = 'population_diplomes_c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=FOR&millesime=2012&typgeo=DEP&search={code}')


class PopulationDiplomesRegionDataset(PopulationDiplomesDataset):
    id = 'population_diplomes_r'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=FOR&millesime=2012&typgeo=REG&search={code}')


class EmploiChiffresDataset(TerritoryDataset):
    order = 4
    title = 'Emploi - Chiffres clés'
    # Institut National de la Statistique et des Etudes Economiques (INSEE).
    organization_id = '534fff81a3a7292c64a77e5c'
    description = '''
        [Population
        ](/datasets/recensement-de-la-population-base-de-donnees-de-chiffres-cles-caracteristiques-de-l-emploi-40535204/)
        de 15 ans ou plus ayant un emploi selon le statut.
    '''.strip()
    temporal_coverage = {'start': 2007, 'end': 2012}


class EmploiChiffresTownDataset(EmploiChiffresDataset):
    id = 'emploi_chiffres_t'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=ACT&nivgeo=COM&codgeo={code}')


class EmploiChiffresCountyDataset(EmploiChiffresDataset):
    id = 'emploi_chiffres_c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=ACT&millesime=2012&typgeo=DEP&search={code}')


class EmploiChiffresRegionDataset(EmploiChiffresDataset):
    id = 'emploi_chiffres_r'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=ACT&millesime=2012&typgeo=REG&search={code}')


class EmploiPopulationDataset(TerritoryDataset):
    order = 5
    title = 'Emploi - Population active'
    # Institut National de la Statistique et des Etudes Economiques (INSEE).
    organization_id = '534fff81a3a7292c64a77e5c'
    description = '''
        [Population
        ](/datasets/recensement-de-la-population-base-de-donnees-de-chiffres-cles-emploi-population-active-40535210/)
        de 15 à 64 ans par type d’activité.
    '''.strip()
    temporal_coverage = {'start': 2007, 'end': 2012}


class EmploiPopulationTownDataset(EmploiPopulationDataset):
    id = 'emploi_population_t'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=EMP&nivgeo=COM&codgeo={code}')


class EmploiPopulationCountyDataset(EmploiPopulationDataset):
    id = 'emploi_population_c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=EMP&millesime=2012&typgeo=DEP&search={code}')


class EmploiPopulationRegionDataset(EmploiPopulationDataset):
    id = 'emploi_population_r'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=EMP&millesime=2012&typgeo=REG&search={code}')


class LogementDataset(TerritoryDataset):
    order = 6
    title = 'Logement'
    # Institut National de la Statistique et des Etudes Economiques (INSEE).
    organization_id = '534fff81a3a7292c64a77e5c'
    description = '''
        [Chiffres clés
        ](/datasets/recensement-de-la-population-base-de-donnees-de-chiffres-cles-logement-40535148/)
        logement.
    '''.strip()
    temporal_coverage = {'start': 2007, 'end': 2012}


class LogementTownDataset(LogementDataset):
    id = 'logement_t'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=LOG&nivgeo=COM&codgeo={code}')


class LogementCountyDataset(LogementDataset):
    id = 'logement_c'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=LOG&millesime=2012&typgeo=DEP&search={code}')


class LogementRegionDataset(LogementDataset):
    id = 'logement_r'
    url_template = ('http://www.insee.fr/fr/themes/tableau_local.asp'
                    '?ref_id=LOG&millesime=2012&typgeo=REG&search={code}')


class Regionales2015Tour2Dataset(ResourceBasedTerritoryDataset):
    order = 7
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
    temporal_coverage = {'start': 2015}


class Regionales2015Tour2TownDataset(Regionales2015Tour2Dataset):
    id = 'elections_regionales_2015_2_t'
    territory_attr = 'name'
    csv_column = 'LIBSUBCOM'


class Regionales2015Tour2CountyDataset(Regionales2015Tour2Dataset):
    id = 'elections_regionales_2015_2_c'
    territory_attr = 'code'
    csv_column = 'CODDPT'


class ZonagesDataset(TerritoryDataset):
    order = 8
    title = 'Zonages des politiques de la ville'
    # Ministère de l'Egalité des Territoires et du Logement.
    organization_id = '534fff8fa3a7292c64a77f3d'
    description = '''
        [ZFU](/datasets/presence-dans-la-commune-d-une-zone-franche-urbaine-zfu-30382923/),
        [ZUS](/datasets/presence-dans-la-commune-d-une-zone-urbaine-sensible-zus-30382883/),
        et autres quartiers du
        [CUCS](/datasets/contrat-urbain-de-cohesion-sociale-cucs-30382914/).
    '''.strip()


class ZonagesTownDataset(ZonagesDataset):
    id = 'zonages_t'
    url_template = (
        'http://sig.ville.gouv.fr/Territoire/{code}/onglet/DonneesLocales')


class ZonagesCountyDataset(ZonagesDataset):
    id = 'zonages_c'
    url_template = (
        'http://sig.ville.gouv.fr/Tableaux/{code_region}{code}')

    @property
    def url(self):
        return self.url_template.format(code=self.territory.code,
                                        code_region=self.territory.parent.code)


class ZonagesRegionDataset(ZonagesDataset):
    id = 'zonages_r'
    url_template = 'http://sig.ville.gouv.fr/Tableaux/{code}'


class ComptesDataset(TerritoryDataset):
    order = 9
    title = 'Comptes de la collectivité'
    # Ministère des finances et des comptes publics.
    organization_id = '534fff8ea3a7292c64a77f02'
    description = '''
        Chiffres Clés, fonctionnement, investissement, fiscalité,
        autofinancement, endettement.
    '''.strip()
    temporal_coverage = {'start': 2000, 'end': 2014}
    license_id = 'notspecified'


class ComptesTownDataset(ComptesDataset):
    id = 'comptes_t'
    url_template = (
        'http://alize2.finances.gouv.fr/communes/eneuro/tableau.php'
        '?icom={icom}&dep=0{dep}&type=BPS&param=0')

    @property
    def url(self):
        return self.url_template.format(icom=self.territory.code[2:5],
                                        dep=self.territory.code[0:2])


class ComptesCountyDataset(ComptesDataset):
    id = 'comptes_c'
    url_template = (
        'http://alize2.finances.gouv.fr/departements/tableau.php'
        '?dep=0{dep}')

    @property
    def url(self):
        return self.url_template.format(dep=self.territory.code[0:2])


class ComptesRegionDataset(ComptesDataset):
    id = 'comptes_r'
    url_template = (
        'http://alize2.finances.gouv.fr/regions/tableau.php'
        '?reg=0{reg}&type=BPS')

    @property
    def url(self):
        return self.url_template.format(reg=self.territory.code)


class BanODBLTownDataset(TerritoryDataset):
    order = 10
    id = 'ban_odbl_t'
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
    license_id = 'odc-odbl'


class AAHDenombrementCAFCountyDataset(ResourceBasedTerritoryDataset):
    order = 11
    id = 'aah_denombrement_caf_c'
    title = 'Allocation aux Adultes Handicapés, dénombrement'
    #  Caisse Nationale des Allocations familiales.
    organization_id = '5595066cc751df4582a453ba'
    description = '''
        [Bénéficiaires percevant l'allocation aux adultes handicapés (AAH)
        ](/datasets/personnes-percevant-l-allocation-aux-adultes-handicapes-aah-par-caf/),
        dénombrement pour le département concerné.
    '''.strip()
    # Equals to: https://www.data.gouv.fr/fr/datasets/personnes-percevant-
    # l-allocation-aux-adultes-handicapes-aah-par-caf/
    dataset_id = '560d9160b595086cd501d755'
    resource_id = '7a870488-f0de-4a40-9d8f-52e065e43c10'
    territory_attr = 'code'
    csv_column = 'dep'
    temporal_coverage = {'start': 1993, 'end': 2015}


class AAHRepartitionCAFCountyDataset(ResourceBasedTerritoryDataset):
    order = 12
    id = 'aah_repartition_caf_c'
    title = 'Allocation aux Adultes Handicapés, répartition'
    #  Caisse Nationale des Allocations familiales.
    organization_id = '5595066cc751df4582a453ba'
    description = '''
        [Bénéficiaires percevant l'allocation aux adultes handicapés (AAH)
        ](/datasets/personnes-percevant-l-allocation-aux-adultes-handicapes-aah-par-caf/),
        répartition pour le département concerné.
    '''.strip()
    # Equals to: https://www.data.gouv.fr/fr/datasets/personnes-percevant-
    # l-allocation-aux-adultes-handicapes-aah-par-caf/
    dataset_id = '560d9160b595086cd501d755'
    resource_id = 'b00056f5-ead5-4d7d-86b3-e1323fc02f0d'
    territory_attr = 'code'
    csv_column = 'Dep'
    temporal_coverage = {'start': 2012, 'end': 2015}


TOWN_DATASETS = {
    'population_t': PopulationTownDataset,
    'population_chiffres_t': PopulationChiffresTownDataset,
    'population_diplomes_t': PopulationDiplomesTownDataset,
    'emploi_chiffres_t': EmploiChiffresTownDataset,
    'emploi_population_t': EmploiPopulationTownDataset,
    'logement_t': LogementTownDataset,
    'elections_regionales_2015_2_t': Regionales2015Tour2TownDataset,
    'zonages_t': ZonagesTownDataset,
    'comptes_t': ComptesTownDataset,
    'ban_odbl_t': BanODBLTownDataset,
}
COUNTY_DATASETS = {
    'population_c': PopulationCountyDataset,
    'population_chiffres_c': PopulationChiffresCountyDataset,
    'population_diplomes_c': PopulationDiplomesCountyDataset,
    'emploi_chiffres_c': EmploiChiffresCountyDataset,
    'emploi_population_c': EmploiPopulationCountyDataset,
    'logement_c': LogementCountyDataset,
    'elections_regionales_2015_2_c': Regionales2015Tour2CountyDataset,
    'zonages_c': ZonagesCountyDataset,
    'comptes_c': ComptesCountyDataset,
    'aah_denombrement_caf_c': AAHDenombrementCAFCountyDataset,
    'aah_repartition_caf_c': AAHRepartitionCAFCountyDataset,
}
REGION_DATASETS = {
    'population_r': PopulationRegionDataset,
    'population_chiffres_r': PopulationChiffresRegionDataset,
    'population_diplomes_r': PopulationDiplomesRegionDataset,
    'emploi_chiffres_r': EmploiChiffresRegionDataset,
    'emploi_population_r': EmploiPopulationRegionDataset,
    'logement_r': LogementRegionDataset,
    'zonages_r': ZonagesRegionDataset,
    'comptes_r': ComptesRegionDataset,
}

TERRITORY_DATASETS['town'].update(TOWN_DATASETS)
TERRITORY_DATASETS['county'].update(COUNTY_DATASETS)
TERRITORY_DATASETS['region'].update(REGION_DATASETS)
