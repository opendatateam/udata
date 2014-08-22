define(['hbs/handlebars', 'jquery'], function(Handlebars, $) {

    var static_root = $('link[rel="static-root"]').attr('href');

    Handlebars.registerHelper('placeholder', function(url, type) {
        return url ? url : static_root + 'img/placeholders/' + type + '.png';
    });

});
