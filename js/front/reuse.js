/**
 * Reuse display page JS module
 */
// Catch all errors
import 'raven';

// ES6 environment
import 'babel-polyfill';

import log from 'logger';

// Legacy widgets
import 'widgets/featured';
import 'widgets/issues-btn';
import 'widgets/discussions-btn';

import Vue from 'vue';

import FollowButton from 'components/buttons/follow.vue';
import ShareButton from 'components/buttons/share.vue';

Vue.use(require('plugins/i18next'));
Vue.use(require('plugins/api'));
Vue.use(require('plugins/tooltips'));

new Vue({
    el: 'body',
    components: {FollowButton, ShareButton},
    ready() {
        log.debug('Reuse display page');
    }
});
