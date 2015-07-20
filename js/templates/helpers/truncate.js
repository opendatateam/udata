define(['handlebars'], function(Handlebars) {

    var DEFAULT_LENGTH = 128;

    return function(value, length) {
        if (!value) {
            return;
        }
        return new Handlebars.SafeString(value.substring(0, length) + '...');
    };

});
