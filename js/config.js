define(['jquery'], function($) {
    'use strict';

    return {
        root: $('link[rel=admin-root]').attr('href'),
        api: $('link[rel=api-specs]').attr('href'),
        title: $('meta[name=site-title]').attr('content'),
        lang: $('html').attr('lang'),
        debug: DEBUG,
        collapse_width: 992,
        theme_static: $('link[rel=theme-static]').attr('href')
    };

});
