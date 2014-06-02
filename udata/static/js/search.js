/**
 * Common search features
 */
define([
    'logger',
    'search/temporal-coverage-facet',
    'widgets/range-picker'
], function(log) {
    'use strict';

    return {
        start: function() {
            log.debug('search started');
        }
    };
});
