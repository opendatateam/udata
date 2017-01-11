/**
 * Bootstrap frontend views
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

// Common Vue.js frontend configuration
Vue.config.debug = config.debug;
Vue.use(require('plugins/api'));
Vue.use(require('plugins/i18next'));
Vue.use(require('plugins/markdown'));
Vue.use(require('plugins/text'));
Vue.use(require('plugins/tooltips'));
Vue.use(require('plugins/util'));
Vue.use(require('plugins/location'));
Vue.use(require('plugins/outside'));

// Site-wide components
Vue.component('site-search', require('components/site-search.vue'));

// Legacy common widgets and helpers (still to be ported)
import 'legacy';

// Expose the uData global
require('expose?uData!udata');
