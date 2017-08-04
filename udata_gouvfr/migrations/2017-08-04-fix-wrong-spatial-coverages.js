/**
 * Fix wrong spatial coverage
 *
 * As a side-effect from the early udata spatial completion
 * some dataset are using Canton/Arrondissement/Iris
 * as spatial coverage instead of cities.
 *
 * This migration is built from a production extract and reaffect
 * dataset to their town spatial coverage.
 *
 * Some of them are not relevant and are just pulled from the spatial coverage
 * (these are unpublished datasets and datasets with multiple level declarations)
 *
 * Some datasets are handled case by case because
 * they use all the inner zone of a bigger ones
 * (ie. all regions for France)
 *
 * NOTE: this migration only works before the new geozones identifier are used
 */

const ZONES = {
    'fr/canton/013-04': 'fr/town/13004',  // Arles
    'fr/canton/022-26': 'fr/town/22360',  // Trégueux
    'fr/canton/02a-01': 'fr/town/2a004',  // Ajaccio
    'fr/canton/02a-02': 'fr/town/2a004',  // Ajaccio
    'fr/canton/02a-03': 'fr/town/2a004',  // Ajaccio
    'fr/canton/02a-04': 'fr/town/2a004',  // Ajaccio
    'fr/canton/02a-05': 'fr/town/2a004',  // Ajaccio
    'fr/canton/051-02': 'fr/town/51075',  // Bourgogne
    'fr/canton/059-06': 'fr/town/59032',  // Aulnoy-les-Valenciennes
    'fr/canton/067-10': 'fr/town/67300',  // Molsheim
    'fr/canton/092-15': 'fr/town/92040',  // Issy-les-Moulineaux
    'fr/canton/092-17': 'fr/town/92048',  // Meudon
    'fr/canton/094-14': 'fr/town/94052',  // Nogent-sur-Marne
    'fr/district/023': 'fr/town/02691',  // St-Quentin
    'fr/district/062': 'fr/town/06088',  // Nice
    'fr/district/102': 'fr/town/10268',  // Nogent-sur-Seine
    'fr/district/103': 'fr/town/10387',  // Troyes
    'fr/district/131': 'fr/town/13001',  // Aix-en-Provence
    'fr/district/133': 'fr/town/13055',  // Marseille
    'fr/district/173': 'fr/town/17300',  // La Rochelle
    'fr/district/212': 'fr/town/21231',  // Dijon
    'fr/district/251': 'fr/town/25056',  // Besançon
    'fr/district/313': 'fr/town/31555',  // Toulouse
    'fr/district/332': 'fr/town/33063',  // Bordeaux
    'fr/district/353': 'fr/town/35238',  // Rennes
    'fr/district/354': 'fr/town/35288',  // Saint-Malon
    'fr/district/372': 'fr/town/37158',  // Montreuil-en-Touraine
    'fr/district/691': 'fr/town/69123',  // Lyon
    'fr/district/672': 'fr/town/67180',  // Haguenau
    'fr/district/733': 'fr/town/73248',  // Saint-Jean-de-Maurienne
    'fr/district/751': 'fr/town/75056',  // Paris
    'fr/district/763': 'fr/town/76540',  // Rouen
    'fr/district/792': 'fr/town/79191',  // Niort
    'fr/district/832': 'fr/town/83137',  // Toulon
    'fr/district/863': 'fr/town/86194',  // Poitiers
    'fr/district/891': 'fr/town/89024',  // Auxerre
    'fr/district/923': 'fr/town/92012',  // Boulogne-Billancourt
    'fr/district/941': 'fr/town/94028',  // Crétail
    'fr/district/942': 'fr/town/94052',  // Nogent-sur-Marne
    'fr/district/9724': 'fr/town/97416',  // Saint-Pierre
    'fr/iris/161490000': '',
    'fr/iris/230890000': '',
    'fr/iris/272970000': '',
    'fr/iris/2A0010000': 'fr/town/2a001',  // Afa
    'fr/iris/2A0060000': 'fr/town/2a006',  // Alata
    'fr/iris/2A0170000': 'fr/town/2a017',  // Appietto
    'fr/iris/2A1030000': 'fr/town/2a103',  // Cuttoli-Corticchiato
    'fr/iris/2A1630000': 'fr/town/2a163',  // Monacia d'Aullène
    'fr/iris/2A2090000': 'fr/town/2a209',  // Peri
    'fr/iris/2A2710000': 'fr/town/2a271',  // Sarrola-Carcopino
    'fr/iris/2A3360000': 'fr/town/2a336',  // Valle-di-Mezzana
    'fr/iris/2A3510000': 'fr/town/2a351',  // Villanova
    'fr/iris/392360000': '',
    'fr/iris/576620000': 'fr/town/57662',  // Suisse
    'fr/iris/671060000': 'fr/town/67106',  // Drusenheim
    'fr/iris/672610000': 'fr/town/67261',  // Lauterbourg
    'fr/iris/673890000': 'fr/town/67389',  // Reichstett
    'fr/iris/820370101': '',
    'fr/iris/820370102': '',
    'fr/iris/900190000': '',
    'fr/iris/920470000': 'fr/town/92047',  // Marnes-la-Coquette
    'fr/iris/920480101': 'fr/town/92048',  // Meudon
    'fr/iris/920720107': 'fr/town/92072',  // Sèvres
    'fr/iris/920750102': 'fr/town/92075',  // Vanves
    'fr/iris/977010102': ''
};

const DATASETS_ZONES = {
    '54880b0dc751df1cc5a3fc15': ['fr/county/10'],  // Aube
    '55509caec751df6dfe190c78': ['country/fr']  // France
};

/**
 * Deduplicate an array by sorting it
 * and then inserting only values that differ from previous entry
 */
function deduplicate(list) {
    return list.sort().filter((item, pos, array) => !pos || item != array[pos - 1]);
}

for (var id in DATASETS_ZONES) {
    const oid = ObjectId(id);
    const result = db.dataset.update(
        {_id: oid},
        {$set: {'spatial.zones': DATASETS_ZONES[id]}}
    );
    print(`Handled specific case for dataset ${id}`);
}

for (var key in ZONES) {
    const new_zone_id = ZONES[key];
    if (new_zone_id) {
        const result = db.dataset.update(
            {'spatial.zones': key},
            {$set: {'spatial.zones.$': new_zone_id}},
            {multi: true}
        );
        print(`Fixed ${result.nModified} datasets for ${key} zone`);
    } else {
        const result = db.dataset.update(
            {'spatial.zones': key},
            {$pull: {'spatial.zones': key}},
            {multi: true}
        );
        print(`Removed ${key} zone in ${result.nModified} datasets`);
    }
}

// Deduplicate
var nb = 0;
db.dataset.aggregate([
    // flatten spatial zones
    {$unwind: '$spatial.zones'},
    // Count (dataset id, zones id) couples
    {$group: {_id: {_id: '$_id', zone: '$spatial.zones'}, count: {$sum: 1}}},
    // Keep doublouns
    {$match: {count: {$gt: 1}}},
    // Group by dataset id
    {$group: {_id: '$_id._id'}},
]).forEach(match => {
    // Deduplicate each match
    const dataset = db.dataset.findOne({_id: match._id});
    db.dataset.update(
        {_id: dataset._id},
        {$set: {'spatial.zones': deduplicate(dataset.spatial.zones)}}
    );
    nb++;
});
print(`Deduplicated zones in ${nb} datasets`);
print('Done. A reindexation is required.');
