define(['api', 'models/base_list'], function(API, List) {
    'use strict';

    var Levels = List.extend({
        name: 'GeoLevels',
        ns: 'spatial',
        fetch: 'spatial_levels'
    });

    return new Levels().fetch();
});
