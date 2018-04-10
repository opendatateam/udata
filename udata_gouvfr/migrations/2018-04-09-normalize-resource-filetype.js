/*
 * resource.filetype: revert to `remote` when `file` and not in `ALLOWED_DOMAINS`
 */

var ALLOWED_DOMAINS = [
    'www.data.gouv.fr', 'static.data.gouv.fr', 'files.data.gouv.fr',
]

var count = 0;
var urlRegex = /^https?\:\/\/([^\/?#]+)(?:[\/?#]|$)/i;

db.dataset.find({'resources.filetype': 'file'}).forEach(function(dataset) {
    if (dataset.resources) {
        dataset.resources.forEach(function(resource) {
            if (resource.filetype && resource.filetype == 'file') {
                var matches = resource.url.match(urlRegex);
                var domain = matches && matches[1];
                // if we can not parse domain, it probably does not belong to `file`
                if (!domain || ALLOWED_DOMAINS.indexOf(domain.toLowerCase()) === -1) {
                    resource.filetype = 'remote';
                    count++;
                }
            }
        });
        db.dataset.save(dataset);
    }
});

print(`${count} resources updated.`);
