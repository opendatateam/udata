/**
 * Webpack spec loader
 */

var SPECS_PATTERN = /\.specs\.js$/;

var context = require.context('.', true, SPECS_PATTERN);
context.keys().forEach(context);
