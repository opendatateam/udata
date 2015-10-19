/*
 * Deduplicate badges on datasets, organizations and reuses
 */

function is_candidate() {
    return this.badges && this.badges.length > 1;
}

/**
 * Iter over the collection to clean badges
 */
function process_collection(collection) {
    var fixed = 0;
    collection.find({'$where': is_candidate}).forEach(function(doc) {
        fixed += process_document(collection, doc) ? 1 : 0;
    });
    print('Fixed ' + fixed + ' document(s) on ' + collection.name);
}

/**
 * Dedplicate badges on a given object
 */
function process_document(collection, doc) {
    var badges = [],
        length = doc.badges.length;

    doc.badges = doc.badges.filter(function(badge) {
        if (badges.indexOf(badge.kind) < 0) {
            badges.push(badge.kind);
            return true;
        }
    });

    if (doc.badges.length !== length) {
        collection.save(doc);
        return true;
    }
}

process_collection(db.dataset);
process_collection(db.organization);
process_collection(db.reuse);
