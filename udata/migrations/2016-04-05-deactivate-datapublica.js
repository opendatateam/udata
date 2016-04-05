/*
 * Deactivate all datasets linking to data-publica
 */

var eurostatId = ObjectId('534fff76a3a7292c64a77ded');
var banqueMondialeId = ObjectId('534fff59a3a7292c64a77cff');

var result = db.dataset.update({
    $or: [
        {organization: eurostatId},
        {organization: banqueMondialeId }
    ]
}, {
    $set: {deleted: new Date()}
}, {
    multi: true
});

print(result.nModified, 'datasets deleted');
