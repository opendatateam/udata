/**
 * Styles
 */
import '../less/admin.less';

// Catch all errors
import 'raven';

// ES6 environment
import 'babel-polyfill';

import 'bootstrap';

import Vue from 'vue';
import config from 'config';
import router from 'admin.routes';

// Ensure retrocompatibily for 0.12.2 replace behavior
Vue.options.replace = false;
Vue.config.debug = config.debug;

Vue.use(require('plugins/util'));
Vue.use(require('plugins/text'));
Vue.use(require('plugins/jquery'));
Vue.use(require('plugins/i18next'));
Vue.use(require('plugins/markdown'));
Vue.use(require('plugins/scroll-to'));
Vue.use(require('plugins/tooltips'));
Vue.use(require('plugins/outside'));

router.start(require('admin.vue'), '#app');
