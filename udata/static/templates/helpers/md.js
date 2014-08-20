define(['hbs/handlebars', 'markdown'], function ( Handlebars, markdown ) {

    Handlebars.registerHelper('md', function (value) {
        return new Handlebars.SafeString(markdown.toHTML(value));
    });

});
