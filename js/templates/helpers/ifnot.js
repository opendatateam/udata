define([], function() {

    return function(test, opts) {
        return !test ? opts.fn(this) : opts.inverse(this);
    };

});
