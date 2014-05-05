/**
 * Main site search
 */
define(['jquery'], function($) {
    'use strict';

    var SEARCH_FOCUS_CLASS = 'col-sm-7 col-lg-8',
        SEARCH_UNFOCUS_CLASS = 'col-sm-2 col-lg-3';

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

});
