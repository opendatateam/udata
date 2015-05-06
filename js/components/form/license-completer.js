define([
    'api',
    'components/form/base-completer.vue'
], function(API, BaseCompleter) {
    'use strict';

    return {
        name: 'license-completer',
        mixins: [BaseCompleter],
        ns: 'datasets',
        endpoint: 'list_licenses',
        selectize: {
            preload: 'focus',
            valueField: 'id',
            labelField: 'title',
            searchField: ['id', 'title'],
        }
        // dataLoaded: function(data) {
        //     return data.map(function(item) {
        //         item.keys = Object.keys(item.keys).map(function(key) {
        //             return item.keys[key];
        //         });
        //         return item
        //     });
        // }

    };
});
