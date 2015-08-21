define(['raven-js', 'config'], function(Raven, config) {
    'use strict';

    var options = {
        logger: 'admin'
    }

    if (config.sentry_dsn) {
        Raven.config(config.sentry_dsn, options).install()
    }

    return Raven;
});
