/**
 * Parse a display date and time using moment.js
 */
define(['moment'], function(moment) {
    return function(value, options) {
        return moment(value).format(options.hash['format'] || 'LLL');
    };
});
