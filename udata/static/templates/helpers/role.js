define(['hbs/handlebars', 'auth'], function(Handlebars, Auth) {

    Handlebars.registerHelper('role', function(value, options) {
        return Auth.has_role(value);
    });

});
