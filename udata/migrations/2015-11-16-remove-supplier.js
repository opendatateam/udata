/**
 * Remove supplier property from datasets
 */
function process_collection(collection) {
    collection.update({supplier: {$exists: true}},
                                 {$unset: {'supplier': 1}}, false, true);
    var count = db.runCommand({getLastError : 1}).n;
    print('Fixed ' + count + ' document(s) on ' + collection.name);
}

process_collection(db.dataset);
