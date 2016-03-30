/**
 * Webpack spec loader
 */
import 'babel-polyfill';

import Vue from 'vue';

Vue.config.silent = true;

const context = require.context('.', true, /\.specs\.js$/);
context.keys().forEach(context);
