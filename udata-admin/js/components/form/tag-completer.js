define([
    'vue',
    'api',
    'components/form/base-completer.vue'
], function(Vue, API, BaseCompleter) {
    'use strict';

    return {
        mixins: [BaseCompleter],
        ns: 'tags',
        endpoint: 'suggest_tags',
        selectize: {
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
