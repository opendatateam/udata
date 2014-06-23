define(['hbs/handlebars'], function(Handlebars) {

    Handlebars.registerHelper('get', function(obj, key) {
        return obj.hasOwnProperty(key) ? obj[key] : '';
    });

});
