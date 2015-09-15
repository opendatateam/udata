// Remove the _cls attribute on badges
var collections = ['dataset', 'reuse', 'organization'];

collections.forEach(function(collection) {
    print('>> Processing badges from '+ collection);
    var docs = db[collection].find({'badges.0': {$exists: true}}),
        badges_count = 0,
        doc_count = 0;

    docs.forEach(function(doc) {
        doc.badges.forEach(function(badge) {
            if (badge._cls) {
                delete badge._cls;
                badges_count++;
            }
        });
        db[collection].save(doc)
        doc_count++;
    });
    print('Processed ' + badges_count + ' badges into ' + doc_count + ' documents.');

});
