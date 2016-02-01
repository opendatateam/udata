/**
 * Typeahead.js/Bloodhound completion definition for reuses
 */
define([
    'jquery',
    'api.light',
    'bloodhound',
    'templates/search/header.hbs',
    'templates/search/suggestion.hbs',
    'i18n'
], function($, API, Bloodhound, header, suggestion, i18n) {
    const MAX = 3;
    const engine = new Bloodhound({
            queryTokenizer: Bloodhound.tokenizers.whitespace,
            datumTokenizer: function(d) {
                return Bloodhound.tokenizers.whitespace(d.name);
            },
            identify: function(d) {
                return d.id;
            },
            remote: {
                url: API.build_url('/reuses/suggest/') + '?q=%QUERY&size=' + MAX,
                wildcard: '%QUERY',
                // Keep until model is uniformised
                transform: function(response) {
                    return response.map((row) => {
                        row.name = row.title;
                        return row;
                    });
                }
            }
        });

    return {
        name: 'reuses',
        source: engine,
        display: 'name',
        limit: MAX,
        templates: {
            header: header({title: i18n._('Reuses')}),
            suggestion: suggestion
        }
    };
});
