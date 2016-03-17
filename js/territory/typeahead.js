/**
 * Typeahead.js/Bloodhound completion definition for territories
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
                url: API.build_url('/territory/suggest/') + '?q=%QUERY&size=' + MAX,
                wildcard: '%QUERY',
                // Keep until model is uniformised
                transform: function(response) {
                    return response.map((row) => {
                        // Display postal code for towns
                        const code = Array.isArray(row.keys.postal) ? row.keys.postal.join(',') : row.keys.postal;
                        row.name = `${row.title} (${code})`;
                        return row;
                    });
                }
            }
        });

    return {
        name: 'territories',
        source: engine,
        display: 'name',
        templates: {
            header: header({title: i18n._('Towns')}),
            suggestion: suggestion
        }
    };
});
