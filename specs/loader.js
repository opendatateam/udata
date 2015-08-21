/**
 * Webpack spec loader
 */
'use strict';

require('babel-core/polyfill');
require('./chai-adapter');

var context = require.context('.', true, /\.specs\.js$/);
context.keys().forEach(context);
