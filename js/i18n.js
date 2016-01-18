/**
 * i18n handling
 */
import i18next from 'i18next-client';
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
    load: 'unspecific',
    interpolationPrefix: '{',
    interpolationSuffix: '}',
    ns: NAMESPACE,
    fallbackLng: false,
    fallbackOnEmpty: true,
    fallbackOnNull: true,
    nsseparator: '::', // Allow to use real sentences as keys
    keyseparator: '$$', // Allow to use real sentences as keys
    resStore: resources
});

export const t = i18next.t;
export const _ = i18next.t;

export default {
    lang,
    _,
    t
};
