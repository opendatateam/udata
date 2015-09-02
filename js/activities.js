'use strict';

// Ensure Babel/ES6 polyfills are loaded
require('babel-core/polyfill');

// Catch all errors
require('raven');

var $ = require('jquery');

var Vue = require('vue'),
    config = require('config');

// Ensure retrocompatibily for 0.12.2 replace behavior
Vue.options.replace = false;
Vue.config.debug = config.debug;

$(require('api')).on('built', function() {
    new Vue(require('components/activities/timeline.vue'));
});

