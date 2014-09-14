define(['hbs/handlebars'], function(Handlebars) {

    var DEFAULT_LENGTH = 128;

    Handlebars.registerHelper('truncate', function(value, length) {
        return new Handlebars.SafeString(value.substring(0, length) + '...');
    });

});
