define(['hbs/handlebars', 'i18n'], function ( Handlebars, i18n ) {

    Handlebars.registerHelper('_', i18n._);

});
