/**
 * User autocompleter
 */
define([
    'vue',
    'api',
    'components/form/base-completer.vue',
    'helpers/placeholders'
], function(Vue, API, BaseCompleter, placeholders) {
    'use strict';

    var template = [
            '<div class="selectize-option">',
            '<div class="logo pull-left">',
            '<img src="{{user.avatar || user.avatar_url || placeholder}}"/>',
            '</div>',
            '{{user.fullname}}',
            '</div>'
        ].join('');


    function render(user) {
        return new Vue({data: {user: user, placeholder: placeholders.user}}).$interpolate(template);
    }

    return {
        name: 'user_completer',
        mixins: [BaseCompleter],
        ns: 'users',
        endpoint: 'suggest_users',
        selectize: {
            valueField: 'id',
            searchField: ['fullname'],
            options: [],
            plugins: ['remove_button'],
            render: {
                option: function(data, escape) {
                    return render(data);
                },
                item: function(data, escape) {
                    return render(data);
                }
            },
        }
    };
});
