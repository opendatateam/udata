define(['hbs/handlebars', 'jquery'], function(Handlebars, $) {

    var theme_static_root = $('link[rel="theme-static-root"]').attr('href');

    Handlebars.registerHelper('theme', function(value) {
        return new Handlebars.SafeString(theme_static_root + value);
    });

});
