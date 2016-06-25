/**
 * Reuse display page JS module
 */
import 'front/bootstrap';

import log from 'logger';

// Legacy widgets
import 'widgets/featured';
import 'widgets/issues-btn';
import 'widgets/discussions-btn';

import Vue from 'vue';

import FollowButton from 'components/buttons/follow.vue';
import ShareButton from 'components/buttons/share.vue';


new Vue({
    el: 'body',
    components: {FollowButton, ShareButton},
    ready() {
        log.debug('Reuse display page');
    }
});
