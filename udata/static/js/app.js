require([
    'logger',
    'routes',
    'domReady',
    'common'
], function(log, routes, domReady) {
    'use strict';

    domReady(function() {
        log.debug('Application starting');
        routes.start();
        log.debug('Application started');
    });
});
