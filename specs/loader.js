/**
 * Webpack spec loader
 */
// Import polyfills first
import 'babel-polyfill';
import 'whatwg-fetch';

import Vue from 'vue';

Vue.config.silent = true;

// Load chai plugins
chai.use(require('chai-dom'));
chai.use(require('chai-string'));
chai.use(require('chai-things'));

const context = require.context('.', true, /\.specs\.js$/);
context.keys().forEach(context);
