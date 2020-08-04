/*
    This module loads common front views requirements
    and export the common behavior as a mixin.

    As it loads polyfills, it needs to be imported first.
 */

// Import common style
import 'less/site.less';

// Catch all errors
import 'raven';

// ES6/DOM environment polyfills
import 'babel-polyfill';
import 'whatwg-fetch';
import 'url-search-params-polyfill';
import 'dom-polyfills';

import config from 'config';
import Vue from 'vue';
import NotificationZone from 'components/notification-zone.vue';
import SiteSearch from 'components/site-search.vue';
import Modal from 'components/modal.vue';
import ModalMixin from 'mixins/modal';

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
Vue.use(require('plugins/clipboard'));

/**
* Frontend views common behavior
*/
export default {
    el: 'body',
    mixins: [ModalMixin],
    components: {NotificationZone, SiteSearch, Modal},
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
    }
};

// Expose the uData global
require('expose?uData!udata');

// Legacy common widgets and helpers (still to be ported)
import 'legacy';
