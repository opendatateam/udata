define(['handlebars', 'helpers/commonmark'], function(Handlebars, commonmark) {

    return function(value) {
        return new Handlebars.SafeString(commonmark.default(value));
    };

});
