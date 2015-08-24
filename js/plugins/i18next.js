import * as i18n from 'i18n';
import moment from 'moment';
import log from 'logger';

export default function(Vue, options) {

    // Register the i18n filter
    Vue.filter('i18n', function(value, options) {
        return i18n._(value, options);
    });

    Vue.filter('dt', function(value, format) {
        return value ? moment(value).format(format || 'LLL') : '-';
    });

    Vue.filter('timeago', function(value) {
        return value ? moment(value).fromNow() : '-';
    });

    Vue.filter('since', function(value) {
        return value ? moment(value).fromNow(true) : '-';
    });

    Vue.directive('i18n', {
        bind: function() {
            this.el.innerHTML = i18n._(this.expression);
        }
    });

    // Make translations accesible globally and on instance
    Vue._ = Vue.prototype._ = i18n._;
    Vue.lang = Vue.prototype.lang = i18n.lang;

    log.debug('Plugin i18next loaded');
};
