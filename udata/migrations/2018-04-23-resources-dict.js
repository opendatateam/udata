/*
 * Migrate faulty `dataset.resources` from {} to []
 * Ensure migrated resources are valid (url && title)
 */

var count = 0;

db.dataset.find().forEach(d => {
    if (d.resources && !(d.resources instanceof Array)) {
        d.resources = Object.keys(d.resources).map(k => d.resources[k]).filter(r => r.url && r.title);
        db.dataset.save(d);
        count++;
    }
});

print(`Migrated ${count} dataset(s).`);
