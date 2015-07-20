define([], function() {

    return function (value, defaultValue) {
        return value != null ? value : defaultValue;
    };

});
