define([
    'jquery',
    'raphael-browserify'
], function($, Raphael) {
    'use strict';

    var Morris = require('imports?raphael=>window.Raphael!exports?window.Morris!morris.js/morris');

    return Morris;
});
