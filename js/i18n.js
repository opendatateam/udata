/**
 * i18n handling
 */
define(['jquery', 'i18next-client', 'moment'], function($, i18next, moment) {
    // Fetch the language once from the html lang attribute
    var lang = $('html').attr('lang'),
        resource = require('locales/udata.' + lang + '.json'),
        store = {};

    store[lang] = {
        udata: resource
    };

    // Initialize required modules
    moment.locale(lang);
    i18next.init({
        lng: lang,
        load: 'unspecific',
        ns: 'udata',
        fallbackLng: false,
        getAsync: false,
        nsseparator: '::', // Allow to use real sentences as keys
        keyseparator: '$$', // Allow to use real sentences as keys
        resStore: store
    });

    return {
        lang: lang,
        t: i18next.t,
        _: i18next.t
    }
});
