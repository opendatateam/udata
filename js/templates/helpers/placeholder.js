define(['helpers/placeholders'], function(placeholders) {

    return function(url, type) {
        return url ? url : placeholders.getFor(type);
    };

});
