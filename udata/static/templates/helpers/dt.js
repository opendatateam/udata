/**
 * Parse a display date and time using moment.js
 */
define(['hbs/handlebars', 'moment'], function(Handlebars, moment) {
    Handlebars.registerHelper('dt', function(value, options) {
        return moment(value).format(options.hash['format'] || 'LLL');
    });
});
