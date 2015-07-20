define(['site/config', 'pubsub', 'logger'], function(config, pubsub, log) {
    'use strict';

    return {
        pubsub: pubsub,
        log: log,
        config: config
    };
});
