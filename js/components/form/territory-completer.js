define([
    'vue',
    'api',
    'components/form/base-completer.vue'
], function(Vue, API, BaseCompleter) {
    'use strict';

    return {
        name: 'territory-completer',
        mixins: [BaseCompleter],
        ns: 'spatial',
        endpoint: 'suggest_territories',
        selectize: {
            valueField: 'id',
            labelField: 'name',
            searchField: ['name', 'code', 'keys'],
            plugins: ['remove_button'],
        },
        dataLoaded: function(data) {
            return data.map(function(item) {
                item.keys = Object.keys(item.keys).map(function(key) {
                    return item.keys[key];
                });
                return item
            });
        }

    };
});
