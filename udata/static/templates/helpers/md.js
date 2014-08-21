define(['hbs/handlebars', 'marked'], function ( Handlebars, marked ) {

    Handlebars.registerHelper('md', function (value) {
        return new Handlebars.SafeString(marked(value));
    });

});
