/**
 * Typeahead.js/Bloodhound completion definition for organizations
 */
define([
    'api.light',
    'bloodhound',
    'templates/search/header.hbs',
    'templates/search/suggestion.hbs',
    'i18n',
    'logger'
], function(API, Bloodhound, header, suggestion, i18n, log) {
    var MAX = 3,
        engine = new Bloodhound({
            name: 'organizations',
            limit: MAX,
            queryTokenizer: Bloodhound.tokenizers.whitespace,
            datumTokenizer: function(d) {
                return Bloodhound.tokenizers.whitespace(d.name);
            },
            identify: function(d) {
                return d.id;
            },
            remote: {
                url: API.build_url('/organizations/suggest/') + '?q=%QUERY&size='+MAX,
                wildcard: '%QUERY'
            }
        });

    return {
        name: 'organizations',
        source: engine,
        display: 'name',
        limit: MAX,
        templates: {
            header: header({title: i18n._('Organizations')}),
            suggestion: suggestion
        }
    };
});
