'use strict';

import $ from 'jquery';

export default {
    root: $('link[rel=admin-root]').attr('href'),
    api: $('link[rel=api-specs]').attr('href'),
    sentry_dsn: $('link[rel=sentry-dsn]').attr('href'),
    title: $('meta[name=site-title]').attr('content') || 'uData Admin',
    lang: $('html').attr('lang') || 'en',
    debug: DEBUG,
    collapse_width: 992,
    theme_static: $('link[rel=theme-static]').attr('href')
};
