/*
 * Remove resources with missing required fields (url or title)
 */

var nbRemoved = 0;

const removedNoTitle = db.dataset.update(
    {resources: {$gt: []}},
    {$pull: {resources: {title: null}}},
    {multi: true}
);

nbRemoved += removedNoTitle.nRemoved;

const removedNoURL = db.dataset.update(
    {resources: {$gt: []}},
    {$pull: {resources: {url: null}}},
    {multi: true}
);

nbRemoved += removedNoURL.nRemoved;

print(`Removed ${nbRemoved} resource(s) without title or URL.`);
