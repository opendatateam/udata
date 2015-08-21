define([
    'vue',
    'api',
    'components/form/base-completer.vue'
], function(Vue, API, BaseCompleter) {
    'use strict';

    return {
        mixins: [BaseCompleter],
        ns: 'datasets',
        endpoint: 'suggest_formats',
        selectize: {
            maxItems: 1,
            valueField: 'text',
            plugins: ['remove_button'],
            create: function(input) {
                return {
                    value: input,
                    text: input
                }
            }
        }
    };
});
