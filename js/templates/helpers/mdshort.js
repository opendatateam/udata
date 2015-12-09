define(['handlebars', 'helpers/commonmark'], function(Handlebars, commonmark) {

    var EXCERPT_TOKEN = '<!--- --- -->',
        DEFAULT_LENGTH = 128;

    return function(value, length) {
        if (!value) {
            return;
        }

        var text, ellipsis;
        if (value.indexOf('<!--- excerpt -->')) {
            value = value.split(EXCERPT_TOKEN, 1)[0];
        }
        ellipsis = value.length >= length ? '...' : '';
        text = commonmark(value.substring(0, length) + ellipsis);
        text = text.replace('<a ', '<span ').replace('</a>', '</span>');
        return new Handlebars.SafeString(text);
    };

});
