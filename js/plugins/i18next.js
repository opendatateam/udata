define(['config', 'i18next', 'moment', 'logger'], function(config, i18next, moment, log) {
    'use strict';

    return function(Vue, options) {
        options = options || {};

        var namespace = options.ns || 'udata-admin',
            lang = config.lang,
            resources = {};

        resources[lang] = {};
        resources[lang][namespace] = require('locales/' + namespace + '.' + lang + '.json');

        moment.locale(lang);
        i18next.init({
            debug: DEBUG,
            lng: lang,
            load: 'unspecific',
            interpolationPrefix: '{',
            interpolationSuffix: '}',
            ns: namespace,
            fallbackLng: false,
            fallbackOnEmpty: true,
            fallbackOnNull: true,
            nsseparator: '::', // Allow to use real sentences as keys
            keyseparator: '$$', // Allow to use real sentences as keys
            resStore: resources
        });

        // Register the i18n filter
        Vue.filter('i18n', function(value, options) {
            return i18next.t(value, options);
        });

        Vue.filter('dt', function(value, format) {
            return moment(value).format(format || 'LLL');
        });

        Vue.filter('timeago', function(value) {
            return moment(value).fromNow();
        });

        Vue.filter('since', function(value) {
            return moment(value).fromNow(true);
        });

        Vue.directive('i18n', {
            bind: function() {
                this.el.innerHTML = i18next.t(this.expression);
            }
        });

        // Make translations accesible globally and on instance
        Vue._ = Vue.prototype._ = i18next.t;
        Vue.lang = Vue.prototype.lang = lang;

        log.debug('Plugin i18next loaded');
    };

});
