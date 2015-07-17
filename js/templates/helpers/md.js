define(['handlebars', 'marked'], function(Handlebars, marked) {

    return function(value) {
        return new Handlebars.SafeString(marked(value));
    };

});
