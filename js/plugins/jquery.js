import $ from 'jquery';

/**
 * Provide some jQuery instance helpers
 */
export function install(Vue) {
    Vue.prototype.$find = function(selector) {
        return $(this.$el).find(selector);
    };
}
