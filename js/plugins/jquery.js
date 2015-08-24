/**
 * Provide some jQuery instance helpers
 */
define(['jquery'], function($) {
    'use strict';

    return function(Vue, options) {  // jshint ignore:line

        Vue.prototype.$find = function(selector) {
            return $(this.$el).find(selector);
        };

    };

});
