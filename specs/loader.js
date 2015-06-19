/**
 * Webpack spec loader
 */
'use strict';

require('./chai-adapter');
// require('./api.specs');

var SPECS_PATTERN = /\.specs\.js$/;

var context = require.context('.', true, SPECS_PATTERN);
context.keys().forEach(context);
