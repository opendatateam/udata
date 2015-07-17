define(['auth'], function(Auth) {

    return function(value, options) {
        return Auth.has_role(value);
    };

});
