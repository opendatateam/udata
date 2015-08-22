'use strict';

/**
 * Styles
 */
require('../less/admin.less');


// Ensure Babel/ES6 polyfills are loaded
require('babel-core/polyfill');

// Catch all errors
require('raven');

var $ = require('jquery');
require('bootstrap');

var Vue = require('vue'),
    config = require('config');

// Ensure retrocompatibily for 0.12.2 replace behavior
Vue.options.replace = false;
Vue.config.debug = config.debug;

Vue.use(require('plugins/util'));
Vue.use(require('plugins/text'));
Vue.use(require('plugins/jquery'));
Vue.use(require('plugins/i18next'));
Vue.use(require('plugins/markdown'));
Vue.use(require('plugins/scroll-to'));
Vue.use(require('plugins/router'), {prefix: config.root});

$(require('api')).on('built', function() {
    var app = new Vue(require('admin.vue'));
    app.$mount('#app');
});

