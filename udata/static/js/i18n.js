/**
 * i18n handling
 */
define(['jquery', 'i18next', 'moment'], function($, i18next, moment) {
    // Fetch the language once from the html lang attribute
    var lang = $('html').attr('lang');

    // Initialize required modules
    moment.lang(lang);
    i18next.init({
        lng: lang,
        ns: 'udata',
        fallbackLng: 'en',
        nsseparator: '::', // Allow to use real sentences as keys
        keyseparator: '$$', // Allow to use real sentences as keys
        resGetPath: require.toUrl('../locales/__ns__.__lng__.json')
    });

    return {
        lang: lang,
        t: i18next.t,
        _: i18next.t
    }
});
