var deleted = 0,
    updated = 0;

/**
 * Extract the dataset identifier from the URL
 * as maaf harvested dataset remote id is the xml file basename
 */
function idFromUrl(url) {
    var parts = url.split('/'),
        filename = parts[parts.length - 1],
        basename = filename.replace('.xml', '').replace('.XML', '');
    return basename;
}

var nb = db.dataset.count({
    'extras.harvest:domain': 'fichiers-publics.agriculture.gouv.fr'
})

print('Found '+nb+' maaf harvested datasets');

var firsts = db.dataset.aggregate([
    // Only process maaf harvested dataset
    {$match: {'extras.harvest:domain': 'fichiers-publics.agriculture.gouv.fr'}},
    // Sort by creation date
    {$sort: {created_at: 1}},
    // Group on remote_id to extract the first created
    {$group: {
        _id: '$extras.harvest:remote_id',
        first: {$first: '$_id'}
    }}
]).forEach(function(item) {
    // Drop extras datasets
    var result = db.dataset.remove({
        _id: { $ne: item.first },
        'extras.harvest:domain': 'fichiers-publics.agriculture.gouv.fr',
        'extras.harvest:remote_id': item._id
    });
    deleted += result.nRemoved;

    // Fix first dataset remote identifier
    result = db.dataset.update(
        {_id: item.first },
        {$set: {'extras.harvest:remote_id': idFromUrl(item._id)}}
    );
    updated += result.nModified;
});

print('Updated ' + updated + ' datasets.');
print('Deleted ' + deleted + ' datasets.');

nb = db.dataset.count({
    'extras.harvest:domain': 'fichiers-publics.agriculture.gouv.fr'
})

print('Kept '+nb+' maaf harvested datasets');
