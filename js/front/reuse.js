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
import 'widgets/share-btn';

import Vue from 'vue';

import FollowButton from 'components/buttons/follow.vue';
import ShareButton from 'components/buttons/share.vue';

import { popover, tooltip } from 'vue-strap';

Vue.use(require('plugins/i18next'));
Vue.use(require('plugins/api'));

new Vue({
    el: 'body',
    components: {popover, tooltip, FollowButton, ShareButton},
    ready() {
        log.debug('Reuse display page');
    }
});
