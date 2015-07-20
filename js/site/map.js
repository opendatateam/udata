define([
    'jquery',
    'logger',
    'dashboard/map'
], function($, log, Map) {
    'use strict';

    var map = new Map('.big-map');

    $(function() {
        map.load();
    });
});


