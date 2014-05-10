/**
 * Typeahead.js/Bloodhound completion definition for datasets
 */
define([
    'jquery',
    'bloodhound',
    'hbs!widgets/ta-header',
    'hbs!widgets/ta-suggestion',
    'i18n',
    'logger'
], function($, Bloodhound, header, suggestion, i18n, log) {
    var MAX = 6,
        engine = new Bloodhound({
            name: 'datasets',
            limit: MAX,
            queryTokenizer: Bloodhound.tokenizers.whitespace,
            datumTokenizer: function(d) {
                return Bloodhound.tokenizers.whitespace(d.name);
            },
            remote: {
                url: '/api/suggest/datasets?q=%QUERY&size='+MAX,
                // Keep until model is uniformised
                filter: function(response) {
                    return $.map(response, function(row, idx) {
                        row.name = row.title;
                        return row;
                    })
                }
            }
        });

    engine.initialize();

    return {
        name: 'datasets',
        source: engine.ttAdapter(),
        displayKey: 'name',
        limit: MAX,
        templates: {
            header: header({title: i18n._('Datasets')}),
            suggestion: suggestion
        }
    };
});
