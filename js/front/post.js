/**
 * Dataset display page JS module
 */
// Catch all errors
import 'raven';

// ES6 environment
import 'babel-polyfill';

import log from 'logger';

import Vue from 'vue';
import config from 'config';

// Components
import ShareButton from 'components/buttons/share.vue';

Vue.config.debug = config.debug;

Vue.use(require('plugins/api'));
Vue.use(require('plugins/text'));
Vue.use(require('plugins/i18next'));
Vue.use(require('plugins/tooltips'));

new Vue({
    el: 'body',
    components: {ShareButton},
    ready() {
        log.debug('Post page ready');
    }
});
