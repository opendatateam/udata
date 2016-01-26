/**
 * i18n handling
 */
import i18next from 'i18next';
import moment from 'moment';
import config from 'config';

export const NAMESPACE = 'udata';
export const lang = config.lang;


const resources = {};

resources[lang] = {};
resources[lang][NAMESPACE] = require('locales/' + NAMESPACE + '.' + lang + '.json');

moment.locale(lang);
i18next.init({
    debug: DEBUG,
    lng: lang,
    load: 'languageOnly',
    interpolation: {
        prefix: '{',
        suffix: '}',
    },
    ns: NAMESPACE,
    defaultNS: NAMESPACE,
    returnEmptyString: true,
    returnNull: true,
    nsSeparator: '::', // Allow to use real sentences as keys
    keySeparator: '$$', // Allow to use real sentences as keys
    resources: resources
});


// Needed fro proper i18next scope
export function _(key, options) {
    return i18next.t(key, options);
};

export default {
    lang,
    _
};
