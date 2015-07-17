define([], function() {

    return function(obj, key) {
        return obj.hasOwnProperty(key) ? obj[key] : '';
    };

});
