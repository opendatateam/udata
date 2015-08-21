import config from 'config';
import i18next from 'i18next-client';
import moment from 'moment';

export const NAMESPACE = 'udata-admin';
export let lang = config.lang;

let resources = {};

resources[lang] = {};
resources[lang][NAMESPACE] = require('js-admin/locales/' + NAMESPACE + '.' + lang + '.json');

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

export let _ = i18next.t;
