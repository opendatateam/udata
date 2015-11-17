/**
 * Remove supplier property from datasets
 */
function process_collection(collection) {
    var updated = collection.update({supplier: {$exists: true}},
                                    {$unset: {'supplier': 1}}, false, true);
    print('Fixed ' + updated.nModified + ' document(s) on ' + collection.name);
}

process_collection(db.dataset);
