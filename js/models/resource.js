define(['api', 'models/base', 'logger'], function(API, Model, log) {
    'use strict';

    var Resource = Model.extend({
        name: 'Resource'
    });

    return Resource;
});
