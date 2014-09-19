/**
 * Typeahead.js/Bloodhound completion definition for organizations
 */
define([
    'api',
    'bloodhound',
    'hbs!templates/search/header',
    'hbs!templates/search/suggestion',
    'i18n',
    'logger'
], function(API, Bloodhound, header, suggestion, i18n, log) {
    var MAX = 2,
        engine = new Bloodhound({
            name: 'organizations',
            limit: MAX,
            queryTokenizer: Bloodhound.tokenizers.whitespace,
            datumTokenizer: function(d) {
                return Bloodhound.tokenizers.whitespace(d.name);
            },
            remote: {
                url: API.build_url('/suggest/organizations') + '?q=%QUERY&size='+MAX
            }
        });

    engine.initialize();

    return {
        name: 'organizations',
        source: engine.ttAdapter(),
        displayKey: 'name',
        limit: MAX,
        templates: {
            header: header({title: i18n._('Organizations')}),
            suggestion: suggestion
        }
    };
});
