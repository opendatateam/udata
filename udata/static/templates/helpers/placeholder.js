define(['hbs/handlebars', 'utils/placeholder'], function(Handlebars, placeholder) {

    Handlebars.registerHelper('placeholder', function(url, type) {
        return url ? url : placeholder(type);
    });

});
