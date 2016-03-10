// ES6 environment
import 'babel-polyfill';

// Catch all errors
import 'raven';

import $ from 'jquery';
import Vue from 'vue';
import config from 'config';
import API from 'api';

// Ensure retrocompatibily for 0.12.2 replace behavior
Vue.options.replace = false;
Vue.config.debug = config.debug;

Vue.use(require('plugins/util'));
Vue.use(require('plugins/text'));
Vue.use(require('plugins/i18next'));
Vue.use(require('plugins/markdown'));

$(API).on('built', function() {
    new Vue(require('components/dashboard/graphs.vue'));
    new Vue(require('components/activities/timeline.vue'));
});
