define(['i18n'], function( i18n ) {

    return function(value, options) {
        return value && typeof value === 'string' ? i18n._(value, options.hash) : '';
    };

});
