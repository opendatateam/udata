define(['utils/placeholder'], function(placeholder) {

    return function(url, type) {
        return url ? url : placeholder.default(type);
    };

});
