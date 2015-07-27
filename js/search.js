/**
 * Common search features
 */
define([
    'jquery',
    'logger',
    'search/temporal-coverage-facet',
    'widgets/range-picker',
], function($, log) {
    'use strict';

    $(function() {
        log.debug('search started');

        // Display toolbar depending on active tab
        $('.search-tabs a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
            var $tab = $(e.target);
            $('.btn-toolbar.wrapper').each(function() {
                var $this = $(this);
                if ($this.data('tab') == $tab.attr('href')) {
                    $this.removeClass('hide');
                } else {
                    $this.addClass('hide');
                }
            });
        });

        $('.advanced-search-panel .list-group-more').on('shown.bs.collapse', function () {
            $('button[data-target="#' + this.id + '"]').hide();
        });

        $('.advanced-search-panel .list-group').on('hidden.bs.collapse shown.bs.collapse', function () {
            $('div[data-target="#' + this.id + '"] .chevrons').first()
                .toggleClass('fa-chevron-down fa-chevron-up');
        });

    });
});
