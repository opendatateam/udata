define(['hbs/handlebars'], function(Handlebars) {

    Handlebars.registerHelper('ifeq', function(a, b, opts) {
        return (a == b) ? opts.fn(this) : opts.inverse(this);
    });

});
