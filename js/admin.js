'use strict';

/**
 * Styles
 */
require('../less/admin.less');

// Catch all errors
require('raven');

var $ = require('jquery');
require('bootstrap');

var Vue = require('vue'),
    config = require('config'),
    router = require('admin.routes');

// Ensure retrocompatibily for 0.12.2 replace behavior
Vue.options.replace = false;
Vue.config.debug = config.debug;

Vue.use(require('plugins/util'));
Vue.use(require('plugins/text'));
Vue.use(require('plugins/jquery'));
Vue.use(require('plugins/i18next'));
Vue.use(require('plugins/markdown'));
Vue.use(require('plugins/scroll-to'));

$(require('api')).on('built', function() {
    router.start(require('admin.vue'), '#app');
});

