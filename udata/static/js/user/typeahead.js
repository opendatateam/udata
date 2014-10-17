/**
 * Typeahead.js/Bloodhound completion definition for datasets
 */
define([
    'jquery',
    'api',
    'bloodhound',
    'hbs!templates/search/header',
    'hbs!templates/search/suggestion',
    'i18n',
    'logger'
], function($, API, Bloodhound, header, suggestion, i18n, log) {
    var MAX = 2,
        engine = new Bloodhound({
            name: 'users',
            limit: MAX,
            queryTokenizer: Bloodhound.tokenizers.whitespace,
            datumTokenizer: function(d) {
                return Bloodhound.tokenizers.whitespace(d.name);
            },
            remote: {
                url: API.build_url('/suggest/users') + '?q=%QUERY&size='+MAX,
                // Keep until model is uniformised
                filter: function(response) {
                    return $.map(response, function(row, idx) {
                        row.name = row.fullname;
                        return row;
                    })
                }
            }
        });

    engine.initialize();

    return {
        name: 'users',
        source: engine.ttAdapter(),
        displayKey: 'name',
        limit: MAX,
        templates: {
            header: header({title: i18n._('Users')}),
            suggestion: suggestion
        }
    };
});
