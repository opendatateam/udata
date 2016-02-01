/**
 * Typeahead.js/Bloodhound completion definition for datasets
 */
define([
    'jquery',
    'api.light',
    'bloodhound',
    'hbs!templates/search/header',
    'hbs!templates/search/suggestion',
    'i18n'
], function($, API, Bloodhound, header, suggestion, i18n) {
    const MAX = 2;
    const engine = new Bloodhound({
            name: 'users',
            limit: MAX,
            queryTokenizer: Bloodhound.tokenizers.whitespace,
            datumTokenizer: function(d) {
                return Bloodhound.tokenizers.whitespace(d.name);
            },
            remote: {
                url: API.build_url('/users/suggest/') + '?q=%QUERY&size=' + MAX,
                // Keep until model is uniformised
                filter: function(response) {
                    return response.map((row) => {
                        row.name = row.first_name + ' ' + row.last_name;
                        return row;
                    });
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
