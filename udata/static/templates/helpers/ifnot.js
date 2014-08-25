define(['hbs/handlebars'], function(Handlebars) {

    Handlebars.registerHelper('ifnot', function(test, opts) {
        return !test ? opts.fn(this) : opts.inverse(this);
    });

});
