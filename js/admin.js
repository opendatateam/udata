/**
 * Styles
 */
import '../less/admin.less';

// Catch all errors
import 'raven';

// ES6 environment
import 'babel-polyfill';

import $ from 'jquery';
import 'bootstrap';

import Vue from 'vue';
import config from 'config';
import router from 'admin.routes';
import API from 'api';

// Ensure retrocompatibily for 0.12.2 replace behavior
Vue.options.replace = false;
Vue.config.debug = config.debug;

Vue.use(require('plugins/util'));
Vue.use(require('plugins/text'));
Vue.use(require('plugins/jquery'));
Vue.use(require('plugins/i18next'));
Vue.use(require('plugins/markdown'));
Vue.use(require('plugins/scroll-to'));


$(API).on('built', function() {
    router.start(require('admin.vue'), '#app');
});
