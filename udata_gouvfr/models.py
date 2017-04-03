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

BASE_POPULATION_URL = 'https://www.insee.fr/fr/statistiques/tableaux/2021173'
POPULATION_FILENAME = 'popleg2013_cc_popleg.xls'
BASE_CHIFFRES_URL = 'https://www.insee.fr/fr/statistiques/tableaux/2020310'
CHIFFRES_FILENAME = 'rp2013_cc_fam.xls'
BASE_FORMATIONS_URL = 'https://www.insee.fr/fr/statistiques/tableaux/2020665'
FORMATIONS_FILENAME = 'rp2013_cc_for.xls'
BASE_EMPLOI_URL = 'https://www.insee.fr/fr/statistiques/tableaux/2020907'
EMPLOI_FILENAME = 'rp2013_cc_act.xls'
BASE_LOGEMENT_URL = 'https://www.insee.fr/fr/statistiques/tableaux/2020507'
LOGEMENT_FILENAME = 'rp2013_cc_log.xls'


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


class PopulationCommuneDataset(PopulationDataset):
    id = 'population_com'
    url_template = BASE_POPULATION_URL + '/COM/{code}/' + POPULATION_FILENAME


class PopulationDepartementDataset(PopulationDataset):
    id = 'population_dep'
    url_template = BASE_POPULATION_URL + '/DEP/{code}/' + POPULATION_FILENAME


class PopulationRegionDataset(PopulationDataset):
    id = 'population_reg'
    url_template = BASE_POPULATION_URL + '/REG/{code}/' + POPULATION_FILENAME


class ChiffresDataset(TerritoryDataset):
    order = 2
    title = 'Chiffres clés'
    # Institut National de la Statistique et des Etudes Economiques (INSEE).
    organization_id = '534fff81a3a7292c64a77e5c'
    description = '''
        [Ménages, couples, familles
        ](/datasets/recensement-de-la-population-base-de-donnees-de-chiffres-cles-evolution-et-structure-de-la--40535162/)
        selon leur composition.
    '''.strip()
    temporal_coverage = {'start': 2007, 'end': 2012}


class ChiffresCommuneDataset(ChiffresDataset):
    id = 'chiffres_com'
    url_template = BASE_CHIFFRES_URL + '/COM/{code}/' + CHIFFRES_FILENAME


class ChiffresDepartementDataset(ChiffresDataset):
    id = 'chiffres_dep'
    url_template = BASE_CHIFFRES_URL + '/DEP/{code}/' + CHIFFRES_FILENAME


class ChiffresRegionDataset(ChiffresDataset):
    id = 'chiffres_reg'
    url_template = BASE_CHIFFRES_URL + '/REG/{code}/' + CHIFFRES_FILENAME


class FormationsDataset(TerritoryDataset):
    order = 3
    title = 'Diplômes - Formation'
    # Institut National de la Statistique et des Etudes Economiques (INSEE).
    organization_id = '534fff81a3a7292c64a77e5c'
    description = '''
        [Scolarisation
        ](/datasets/recensement-de-la-population-base-de-donnees-de-chiffres-cles-diplomes-formation-40535144/)
        selon l’âge et le sexe.
    '''.strip()
    temporal_coverage = {'start': 2007, 'end': 2012}


class FormationsCommuneDataset(FormationsDataset):
    id = 'formations_com'
    url_template = BASE_FORMATIONS_URL + '/COM/{code}/' + FORMATIONS_FILENAME


class FormationsDepartementDataset(FormationsDataset):
    id = 'formations_dep'
    url_template = BASE_FORMATIONS_URL + '/DEP/{code}/' + FORMATIONS_FILENAME


class FormationsRegionDataset(FormationsDataset):
    id = 'formations_reg'
    url_template = BASE_FORMATIONS_URL + '/REG/{code}/' + FORMATIONS_FILENAME


class EmploiDataset(TerritoryDataset):
    order = 4
    title = 'Emploi'
    # Institut National de la Statistique et des Etudes Economiques (INSEE).
    organization_id = '534fff81a3a7292c64a77e5c'
    description = '''
        [Population
        ](/datasets/recensement-de-la-population-base-de-donnees-de-chiffres-cles-caracteristiques-de-l-emploi-40535204/)
        de 15 ans ou plus ayant un emploi selon le statut.
    '''.strip()
    temporal_coverage = {'start': 2007, 'end': 2012}


class EmploiCommuneDataset(EmploiDataset):
    id = 'emploi_com'
    url_template = BASE_EMPLOI_URL + '/COM/{code}/' + EMPLOI_FILENAME


class EmploiDepartementDataset(EmploiDataset):
    id = 'emploi_dep'
    url_template = BASE_EMPLOI_URL + '/DEP/{code}/' + EMPLOI_FILENAME


class EmploiRegionDataset(EmploiDataset):
    id = 'emploi_reg'
    url_template = BASE_EMPLOI_URL + '/REG/{code}/' + EMPLOI_FILENAME


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


class LogementCommuneDataset(LogementDataset):
    id = 'logement_com'
    url_template = BASE_LOGEMENT_URL + '/COM/{code}/' + LOGEMENT_FILENAME


class LogementDepartementDataset(LogementDataset):
    id = 'logement_dep'
    url_template = BASE_LOGEMENT_URL + '/DEP/{code}/' + LOGEMENT_FILENAME


class LogementRegionDataset(LogementDataset):
    id = 'logement_reg'
    url_template = BASE_LOGEMENT_URL + '/REG/{code}/' + LOGEMENT_FILENAME


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


class Regionales2015Tour2CommuneDataset(Regionales2015Tour2Dataset):
    id = 'elections_regionales_2015_2_com'
    territory_attr = 'name'
    csv_column = 'LIBSUBCOM'


class Regionales2015Tour2DepartementDataset(Regionales2015Tour2Dataset):
    id = 'elections_regionales_2015_2_dep'
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


class ZonagesCommuneDataset(ZonagesDataset):
    id = 'zonages_com'
    url_template = (
        'http://sig.ville.gouv.fr/Territoire/{code}/onglet/DonneesLocales')


class ZonagesDepartementDataset(ZonagesDataset):
    id = 'zonages_dep'
    url_template = (
        'http://sig.ville.gouv.fr/Tableaux/{code_region}{code}')

    @property
    def url(self):
        return self.url_template.format(code=self.territory.code,
                                        code_region=self.territory.parent.code)


class ZonagesRegionDataset(ZonagesDataset):
    id = 'zonages_reg'
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


class ComptesCommuneDataset(ComptesDataset):
    id = 'comptes_com'
    url_template = (
        'http://alize2.finances.gouv.fr/communes/eneuro/tableau.php'
        '?icom={icom}&dep=0{dep}&type=BPS&param=0')

    @property
    def url(self):
        return self.url_template.format(icom=self.territory.code[2:5],
                                        dep=self.territory.code[0:2])


class ComptesDepartementDataset(ComptesDataset):
    id = 'comptes_dep'
    url_template = (
        'http://alize2.finances.gouv.fr/departements/tableau.php'
        '?dep=0{dep}')

    @property
    def url(self):
        return self.url_template.format(dep=self.territory.code[0:2])


class ComptesRegionDataset(ComptesDataset):
    id = 'comptes_reg'
    url_template = (
        'http://alize2.finances.gouv.fr/regions/tableau.php'
        '?reg=0{reg}&type=BPS')

    @property
    def url(self):
        return self.url_template.format(reg=self.territory.code)


class BanODBLCommuneDataset(TerritoryDataset):
    order = 10
    id = 'ban_odbl_com'
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


class AAHDenombrementCAFDepartementDataset(ResourceBasedTerritoryDataset):
    order = 11
    id = 'aah_denombrement_caf_dep'
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


class AAHRepartitionCAFDepartementDataset(ResourceBasedTerritoryDataset):
    order = 12
    id = 'aah_repartition_caf_dep'
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
    'population_com': PopulationCommuneDataset,
    'chiffres_com': ChiffresCommuneDataset,
    'formations_com': FormationsCommuneDataset,
    'emploi_com': EmploiCommuneDataset,
    'logement_com': LogementCommuneDataset,
    'elections_regionales_2015_2_com': Regionales2015Tour2CommuneDataset,
    'zonages_com': ZonagesCommuneDataset,
    'comptes_com': ComptesCommuneDataset,
    'ban_odbl_com': BanODBLCommuneDataset,
}
COUNTY_DATASETS = {
    'population_dep': PopulationDepartementDataset,
    'chiffres_dep': ChiffresDepartementDataset,
    'formations_dep': FormationsDepartementDataset,
    'emploi_dep': EmploiDepartementDataset,
    'logement_dep': LogementDepartementDataset,
    'elections_regionales_2015_2_dep': Regionales2015Tour2DepartementDataset,
    'zonages_dep': ZonagesDepartementDataset,
    'comptes_dep': ComptesDepartementDataset,
    'aah_denombrement_caf_dep': AAHDenombrementCAFDepartementDataset,
    'aah_repartition_caf_dep': AAHRepartitionCAFDepartementDataset,
}
REGION_DATASETS = {
    'population_reg': PopulationRegionDataset,
    'chiffres_reg': ChiffresRegionDataset,
    'formations_reg': FormationsRegionDataset,
    'emploi_reg': EmploiRegionDataset,
    'logement_reg': LogementRegionDataset,
    'zonages_reg': ZonagesRegionDataset,
    'comptes_reg': ComptesRegionDataset,
}

TERRITORY_DATASETS['COM'].update(TOWN_DATASETS)
TERRITORY_DATASETS['DEP'].update(COUNTY_DATASETS)
TERRITORY_DATASETS['REG'].update(REGION_DATASETS)
