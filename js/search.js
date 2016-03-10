/**
 * Common search features
 */

// ES6 environment
import 'babel-polyfill';

import $ from 'jquery';
import log from 'logger';
import 'search/temporal-coverage-facet';
import 'widgets/range-picker';

$(function() {
    log.debug('search started');

    // Display toolbar depending on active tab
    $('.search-tabs a[data-toggle="tab"]').on('shown.bs.tab', function(e) {
        const $tab = $(e.target);
        $('.btn-toolbar.wrapper').each(function() {
            const $this = $(this);
            if ($this.data('tab') === $tab.attr('href')) {
                $this.removeClass('hide');
            } else {
                $this.addClass('hide');
            }
        });
    });

    $('.advanced-search-panel .list-group-more').on('shown.bs.collapse', function() {
        $('button[data-target="#' + this.id + '"]').hide();
    });

    $('.advanced-search-panel .list-group').on('hidden.bs.collapse shown.bs.collapse', function(e) {
        // Do not flip chevrons if the "More results" link is clicked.
        if (e.target.id.endsWith('-more')) return;
        $('div[data-target="#' + this.id + '"] .chevrons').first()
            .toggleClass('fa-chevron-down fa-chevron-up');
    });
});
