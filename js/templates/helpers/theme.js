define(['handlebars', 'jquery', 'config'], function(Handlebars, $, config) {

    return function(value) {
        return new Handlebars.SafeString(config.theme_static + value);
    };

});
