/*
    This module loads common front views requirements
    and export the common behavior as a mixin.

    As it loads polyfills, it needs to be imported first.
 */

// Import common style
import 'less/site.less';

// Catch all errors
import 'raven';

// ES6 environment polyfills
import 'babel-polyfill';
import 'whatwg-fetch';

import config from 'config';
import Vue from 'vue';
import NotificationZone from 'components/notification-zone.vue';
import SiteSearch from 'components/site-search.vue';

// Common Vue.js frontend configuration
Vue.config.debug = config.debug;

// FrontEnd plugins
Vue.use(require('plugins/api'));
Vue.use(require('plugins/auth'));
Vue.use(require('plugins/i18next'));
Vue.use(require('plugins/markdown'));
Vue.use(require('plugins/text'));
Vue.use(require('plugins/tooltips'));
Vue.use(require('plugins/util'));
Vue.use(require('plugins/location'));
Vue.use(require('plugins/outside'));
Vue.use(require('plugins/scroll-to'));


/**
* Frontend views common behavior
*/
export default {
    el: 'body',
    components: {NotificationZone, SiteSearch},
    data() {
        return {
            notifications: [],
        };
    },
    events: {
        'notify:success': function(title, details) {
            this.notifications.push({type: 'success', icon: 'check', title, details});
        },
        'notify:error': function(title, details) {
            this.notifications.push({type: 'danger', icon: 'exclamation-triangle', title, details});
        },
        'notify:close': function(notification) {
            const index = this.notifications.indexOf(notification);
            this.notifications.splice(index, 1);
        }
    },
    methods: {
        /**
         * Insert a modal Vue in the application.
         * @param  {Object} options     The modal component definition (options passed to Vue.extend())
         * @param  {Object} data        Data to assign to modal properties
         * @return {Vue}                The child instanciated vm
         */
        $modal(options, data) {
            const constructor = Vue.extend(options);
            return new constructor({
                el: this.$els.modal,  // This is the modal placeholder in Jinja template
                replace: false,  // Needed while all components are not migrated to replace: true behavior
                parent: this,
                propsData: data
            });
        },
    }
};

// Expose the uData global
require('expose?uData!udata');

// Legacy common widgets and helpers (still to be ported)
import 'legacy';
