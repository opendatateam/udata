define(['hbs/handlebars', 'marked'], function ( Handlebars, marked ) {

    var EXCERPT_TOKEN = '<!--- excerpt -->',
        DEFAULT_LENGTH = 128;

    Handlebars.registerHelper('mdshort', function (value, length) {
        if (value.indexOf('<!--- excerpt -->')) {
            value = value.split(EXCERPT_TOKEN, 1)[0];
        }
        return new Handlebars.SafeString(marked(value.substring(0, length)));
    });

});
