/**
 * Main site search
 */
define([
    'jquery',
    'dataset/typeahead',
    'reuse/typeahead',
    'organization/typeahead',
    // 'user/typeahead',
    'typeahead'
], function($, datasets, reuses, organizations) {
    'use strict';

    var SEARCH_FOCUS_CLASS = 'col-sm-7 col-lg-8',
        SEARCH_UNFOCUS_CLASS = 'col-sm-2 col-lg-3',
        options = {
            highlight: true,
            classNames: {
                menu: 'tt-dropdown-menu'
            }
        };

    // Expandable main search bar
    $('#main-search')
        .focusin(function() {
            $('.collapse-on-search').addClass('hide');
            $(this).closest('.navbar-nav')
                .removeClass(SEARCH_UNFOCUS_CLASS)
                .addClass(SEARCH_FOCUS_CLASS);
        })
        .focusout(function() {
            $(this).closest('.navbar-nav')
                .removeClass(SEARCH_FOCUS_CLASS)
                .addClass(SEARCH_UNFOCUS_CLASS);
            $('.collapse-on-search').removeClass('hide');
        })
    ;

    // Typeahead
    $('#main-search')
        .typeahead(options, organizations, datasets, reuses)
        .on('typeahead:select', function(e, data, datatype) {
            window.location = data.page
        });

});
