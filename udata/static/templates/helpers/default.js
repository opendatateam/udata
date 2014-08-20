define(['hbs/handlebars'], function ( Handlebars ) {

    Handlebars.registerHelper('default', function (value, defaultValue) {
        return value != null ? value : defaultValue;
    });

});
