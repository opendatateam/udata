define(['handlebars', 'jquery'], function(Handlebars, $) {

    var theme_static_root = $('link[rel="theme-static-root"]').attr('href');

    return function(value) {
        return new Handlebars.SafeString(theme_static_root + value);
    };

});
