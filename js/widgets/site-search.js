/**
 * Main site search
 */
 const config = require('config');

define([
    'jquery',
    'dataset/typeahead',
    'reuse/typeahead',
    'organization/typeahead',
    'territory/typeahead',
    'typeahead'
], function($, datasets, reuses, organizations, territories) {
    'use strict';

    const SEARCH_FOCUS_CLASS = 'col-sm-7 col-lg-8';
    const SEARCH_UNFOCUS_CLASS = 'col-sm-2 col-lg-3';
    const options = {
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
    let providers = [organizations, datasets, reuses];
    if (config.territory_enabled) {
        providers.push(territories);
    }
    $('#main-search')
        .typeahead(options, ...providers)
        .on('typeahead:select', (e, data, datatype) => {
            window.location = data.page;
        });

});
