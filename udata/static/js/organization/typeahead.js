/**
 * Typeahead.js/Bloodhound completion definition for organizations
 */
define([
    'bloodhound',
    'hbs!widgets/ta-header',
    'hbs!widgets/ta-suggestion',
    'logger'
], function(Bloodhound, header, suggestion, log) {
    var MAX = 2,
        engine = new Bloodhound({
            name: 'organizations',
            limit: MAX,
            queryTokenizer: Bloodhound.tokenizers.whitespace,
            datumTokenizer: function(d) {
                return Bloodhound.tokenizers.whitespace(d.name);
            },
            remote: {
                url: '/api/suggest/organizations?q=%QUERY&size='+MAX
            }
        });

    engine.initialize();

    return {
        name: 'organizations',
        source: engine.ttAdapter(),
        displayKey: 'name',
        limit: MAX,
        templates: {
            header: header({title: 'Organizations'}),
            suggestion: suggestion
        }
    };
});
