define([
    'jquery',
    'logger',
    'dashboard/map'
], function($, log, Map) {
    'use strict';

    var map = new Map('.big-map');

    return {
        start: function() {
            map.load();
        }
    };
});


